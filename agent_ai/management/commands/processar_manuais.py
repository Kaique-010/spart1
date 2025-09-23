import os
import requests
import hashlib
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files.base import ContentFile
from agent_ai.models import Manual, ManualProcessado, ImagemManual
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Processa manuais existentes para gerar dados nas novas tabelas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limita o número de manuais a processar'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Reprocessa manuais já processados'
        )

    def handle(self, *args, **options):
        limit = options.get('limit')
        force = options.get('force')
        
        # Busca manuais que ainda não foram processados
        if force:
            manuais = Manual.objects.all()
            self.stdout.write(self.style.WARNING('Modo force ativado - reprocessando todos os manuais'))
        else:
            manuais_processados_ids = ManualProcessado.objects.values_list('manual_id', flat=True)
            manuais = Manual.objects.exclude(id__in=manuais_processados_ids)
        
        if limit:
            manuais = manuais[:limit]
        
        total = manuais.count()
        self.stdout.write(f'Processando {total} manuais...')
        
        for i, manual in enumerate(manuais, 1):
            try:
                self.stdout.write(f'[{i}/{total}] Processando: {manual.title}')
                
                # Remove manual processado existente se force=True
                if force:
                    ManualProcessado.objects.filter(manual=manual).delete()
                
                # Busca o conteúdo HTML da URL do manual
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
                }
                
                response = requests.get(manual.url, headers=headers, verify=False, timeout=30)
                response.raise_for_status()
                
                # Processa o HTML para extrair conteúdo principal
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Encontrar o conteúdo principal (usando lógica do manual_converter.py)
                main_content = soup.find('div', class_=lambda x: x and 'article-content' in x)
                
                if not main_content:
                    main_content = soup.find('article')
                
                if not main_content:
                    main_content = soup.find('div', class_=lambda x: x and 'content' in ' '.join(x).lower())
                
                if not main_content:
                    # Procurar pela div com mais texto
                    all_divs = soup.find_all('div')
                    if all_divs:
                        text_lengths = [(div, len(div.get_text(strip=True))) for div in all_divs]
                        text_lengths.sort(key=lambda x: x[1], reverse=True)
                        main_content = text_lengths[0][0]
                
                if not main_content:
                    raise Exception("Não foi possível encontrar o conteúdo principal")
                
                # Remove elementos desnecessários
                for script in main_content(["script", "style", "nav", "header", "footer"]):
                    script.decompose()
                
                # Extrai texto limpo
                texto_limpo = main_content.get_text(separator='\n', strip=True)
                
                # Cria ou atualiza o ManualProcessado
                manual_processado, created = ManualProcessado.objects.get_or_create(
                    manual_id=manual.id,
                    defaults={
                        'titulo': manual.title,
                        'url_original': manual.url,
                        'conteudo_markdown': texto_limpo,
                        'conteudo_html_original': str(main_content)
                    }
                )
                
                if not created:
                    # Atualiza se já existe
                    manual_processado.titulo = manual.title
                    manual_processado.url_original = manual.url
                    manual_processado.conteudo_markdown = texto_limpo
                    manual_processado.conteudo_html_original = str(main_content)
                    # Limpar imagens antigas
                    manual_processado.imagens.all().delete()
                
                # Processa imagens usando lógica do manual_converter.py
                base_url = '/'.join(manual.url.split('/')[:3])  # https://spartacus.movidesk.com
                imagens_salvas = self.processar_imagens(main_content, base_url, manual_processado)
                
                # Atualiza total de imagens
                manual_processado.total_imagens = len(imagens_salvas)
                manual_processado.save()  # Isso gerará o embedding automaticamente
                
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Manual processado com {len(imagens_salvas)} imagens')
                )
                
            except Exception as e:
                logger.error(f'Erro ao processar manual {manual.title}: {e}')
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Erro: {e}')
                )
                continue
        
        self.stdout.write(
            self.style.SUCCESS(f'Processamento concluído! {total} manuais processados.')
        )
    
    def processar_imagens(self, content, base_url, manual_processado):
        """Processa imagens no conteúdo HTML e salva no banco de dados."""
        imagens_salvas = []
        
        # Encontrar todas as imagens
        img_tags = content.find_all('img')
        self.stdout.write(f'  - Encontradas {len(img_tags)} imagens para processar')
        
        for i, img in enumerate(img_tags):
            src = img.get('src')
            if not src:
                continue
                
            # Converter URL relativa para absoluta
            if src.startswith('//'):
                absolute_url = 'https:' + src
            elif src.startswith('/'):
                absolute_url = urljoin(base_url, src)
            elif src.startswith('http'):
                absolute_url = src
            else:
                absolute_url = urljoin(base_url, src)
            
            # Baixar e salvar a imagem no banco
            alt_text = img.get('alt', 'Imagem')
            imagem_obj = self.baixar_e_salvar_imagem(
                absolute_url, 
                manual_processado, 
                ordem=i+1, 
                alt_text=alt_text
            )
            
            if imagem_obj:
                imagens_salvas.append(imagem_obj)
        
        return imagens_salvas
    
    def baixar_e_salvar_imagem(self, url, manual_processado, ordem, alt_text="Imagem"):
        """Baixa uma imagem e salva no banco de dados."""
        try:
            response = requests.get(url, stream=True, verify=False, timeout=30)
            response.raise_for_status()
            
            # Gerar hash do conteúdo
            content = response.content
            hash_obj = hashlib.md5(content)
            hash_hex = hash_obj.hexdigest()
            
            # Verificar se já existe uma imagem com este hash para este manual
            existing_image = ImagemManual.objects.filter(
                manual_processado=manual_processado,
                hash_conteudo=hash_hex
            ).first()
            
            if existing_image:
                self.stdout.write(f'    - Imagem já existe: {existing_image.nome_arquivo}')
                return existing_image
            
            # Determinar extensão do arquivo
            content_type = response.headers.get('content-type', '')
            if 'jpeg' in content_type or 'jpg' in content_type:
                ext = '.jpg'
            elif 'png' in content_type:
                ext = '.png'
            elif 'gif' in content_type:
                ext = '.gif'
            else:
                ext = '.jpg'  # default
            
            filename = f"manual_{manual_processado.manual_id}_img_{hash_hex[:8]}{ext}"
            
            # Criar objeto ContentFile
            content_file = ContentFile(content, name=filename)
            
            # Criar e salvar a imagem no banco
            imagem = ImagemManual.objects.create(
                manual_processado=manual_processado,
                url_original=url,
                nome_arquivo=filename,
                alt_text=alt_text,
                ordem=ordem,
                hash_conteudo=hash_hex,
                tamanho_bytes=len(content)
            )
            
            # Salvar o arquivo
            imagem.arquivo_imagem.save(filename, content_file, save=True)
            
            self.stdout.write(f'    - Imagem salva: {filename}')
            return imagem
            
        except Exception as e:
            logger.error(f'Erro ao baixar e salvar imagem {url}: {e}')
            return None