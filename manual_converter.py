import os
import sys
import django
import requests
import re
from docling.document_converter import DocumentConverter
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import hashlib
from pathlib import Path
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spart.settings')
django.setup()

from agent_ai.models import Manual, ManualProcessado, ImagemManual

def convert_document_to_markdown(source):
    """Converte documento usando docling."""
    converter = DocumentConverter()
    return converter.convert(source)

def download_and_save_image_to_db(url, manual_processado, ordem, alt_text="Imagem"):
    """Baixa uma imagem e salva no banco de dados."""
    try:
        response = requests.get(url, stream=True, verify=False)
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
            print(f"Imagem já existe no banco: {existing_image.nome_arquivo}")
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
        
        print(f"Imagem salva no banco: {filename}")
        return imagem
        
    except Exception as e:
        print(f"Erro ao baixar e salvar imagem {url}: {e}")
        return None

def process_images_in_content(content, base_url, manual_processado):
    """Processa imagens no conteúdo HTML e salva no banco de dados."""
    imagens_salvas = []
    
    # Encontrar todas as imagens
    img_tags = content.find_all('img')
    print(f"Encontradas {len(img_tags)} imagens para processar")
    
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
        
        print(f"Processando imagem {i+1}: {absolute_url}")
        
        # Baixar e salvar a imagem no banco
        alt_text = img.get('alt', 'Imagem')
        imagem_obj = download_and_save_image_to_db(
            absolute_url, 
            manual_processado, 
            ordem=i+1, 
            alt_text=alt_text
        )
        
        if imagem_obj:
            imagens_salvas.append(imagem_obj)
            # Substituir a tag img por um comentário com referência
            img.replace_with(content.new_string(f'<!-- image:{imagem_obj.id} -->'))
    
    return imagens_salvas

def enhance_markdown_with_images(markdown_content, imagens_salvas):
    """Melhora o markdown substituindo comentários de imagem por referências reais."""
    enhanced_markdown = markdown_content
    
    # Substituir comentários <!-- image:id --> por referências de imagem
    for imagem in imagens_salvas:
        # Procurar por comentários de imagem específicos e substituir
        image_comment_pattern = f'<!-- image:{imagem.id} -->'
        if image_comment_pattern in enhanced_markdown:
            # Criar referência markdown para a imagem usando URL do Django
            img_url = imagem.get_url_servida() or f'/media/{imagem.arquivo_imagem.name}'
            img_reference = f"![{imagem.alt_text}]({img_url})"
            # Substituir a ocorrência específica
            enhanced_markdown = enhanced_markdown.replace(image_comment_pattern, img_reference)
    
    # Adicionar seção com lista de todas as imagens no final
    if imagens_salvas:
        enhanced_markdown += "\n\n## Imagens do Manual\n\n"
        for imagem in imagens_salvas:
            img_url = imagem.get_url_servida() or f'/media/{imagem.arquivo_imagem.name}'
            enhanced_markdown += f"- ![{imagem.alt_text}]({img_url})\n"
            enhanced_markdown += f"  - Arquivo: `{imagem.nome_arquivo}`\n"
            enhanced_markdown += f"  - URL original: {imagem.url_original}\n\n"
    
    return enhanced_markdown

def convert_html_to_markdown_manual(content, title):
    """Conversão manual básica de HTML para Markdown como fallback."""
    # Implementação básica de conversão HTML para Markdown
    text = content.get_text(separator='\n', strip=True)
    return f"# {title}\n\n{text}"

def buscar_manual_com_docling(manual_id):
    """Busca um manual específico e converte para markdown extraindo apenas o conteúdo relevante."""
    try:
        manual = Manual.objects.get(id=manual_id)
        print(f"Processando manual ID {manual_id}: {manual.title}")
        
        # Baixar o conteúdo HTML
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
        }
        
        response = requests.get(manual.url, headers=headers, verify=False, timeout=30)
        response.raise_for_status()
        
        # Processar HTML para extrair apenas o conteúdo relevante
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remover elementos de navegação indesejados
        # Remover elementos que contenham "Terminal#" seguido de números
        for element in soup.find_all(text=lambda text: text and re.search(r'Terminal#\d+-\d+', text)):
            if element.parent:
                element.parent.decompose()
        
        # Encontrar o conteúdo principal
        # Prioridade 1: div com classe 'article-content'
        main_content = soup.find('div', class_=lambda x: x and 'article-content' in x)
        
        if not main_content:
            # Prioridade 2: elemento article
            main_content = soup.find('article')
        
        if not main_content:
            # Prioridade 3: div com classe relacionada a conteúdo
            main_content = soup.find('div', class_=lambda x: x and 'content' in ' '.join(x).lower())
        
        if not main_content:
            # Prioridade 4: procurar pela div com mais texto
            all_divs = soup.find_all('div')
            if all_divs:
                text_lengths = [(div, len(div.get_text(strip=True))) for div in all_divs]
                text_lengths.sort(key=lambda x: x[1], reverse=True)
                main_content = text_lengths[0][0]
        
        if not main_content:
            raise Exception("Não foi possível encontrar o conteúdo principal")
        
        # Verificar se já existe um manual processado
        manual_processado, created = ManualProcessado.objects.get_or_create(
            manual_id=manual_id,
            defaults={
                'titulo': manual.title,
                'url_original': manual.url,
                'conteudo_html_original': str(main_content)
            }
        )
        
        if not created:
            print(f"Manual {manual_id} já foi processado. Atualizando...")
            manual_processado.titulo = manual.title
            manual_processado.url_original = manual.url
            manual_processado.conteudo_html_original = str(main_content)
            # Limpar imagens antigas
            manual_processado.imagens.all().delete()
        
        # Processar imagens: baixar e salvar no banco
        base_url = '/'.join(manual.url.split('/')[:3])  # https://spartacus.movidesk.com
        print(f"Processando imagens do manual...")
        imagens_salvas = process_images_in_content(main_content, base_url, manual_processado)
        print(f"Total de imagens processadas: {len(imagens_salvas)}")
        
        # Criar HTML limpo apenas com o conteúdo principal
        clean_html = f"<html><head><title>{manual.title}</title></head><body>{main_content}</body></html>"
        
        # Salvar em arquivo temporário
        temp_file = f"temp_manual_{manual_id}.html"
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(clean_html)
        
        # Converter com docling
        try:
            result = convert_document_to_markdown(temp_file)
            markdown_content = result.document.export_to_markdown()
        except Exception as e:
            print(f"Erro na conversão com docling: {e}")
            # Fallback: conversão manual básica
            markdown_content = convert_html_to_markdown_manual(main_content, manual.title)
        
        # Limpar arquivo temporário
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        # Melhorar o markdown com informações das imagens
        enhanced_markdown = enhance_markdown_with_images(markdown_content, imagens_salvas)
        
        print("\n=== CONTEÚDO EM MARKDOWN ===")
        print(enhanced_markdown[:500] + "..." if len(enhanced_markdown) > 500 else enhanced_markdown)
        
        # Salvar o conteúdo markdown no banco
        manual_processado.conteudo_markdown = enhanced_markdown
        manual_processado.total_imagens = len(imagens_salvas)
        manual_processado.save()  # Isso também gerará o embedding automaticamente
        
        print(f"\nManual {manual_id} salvo no banco de dados:")
        print(f"- Título: {manual_processado.titulo}")
        print(f"- Total de imagens: {len(imagens_salvas)}")
        print(f"- Total de caracteres: {len(enhanced_markdown)}")
        print(f"- Embedding gerado: {'Sim' if manual_processado.embedding else 'Não'}")
        
        return enhanced_markdown
        
    except Manual.DoesNotExist:
        print(f"Manual com ID {manual_id} não encontrado.")
        return None
    except Exception as e:
        print(f"Erro durante a conversão: {e}")
        return None

def converter_todos_manuais():
    """Converte todos os manuais cadastrados para markdown."""
    manuais = Manual.objects.all()
    print(f"Encontrados {manuais.count()} manuais para converter.")
    
    resultados = []
    for manual in manuais:
        print(f"\n--- Convertendo Manual ID {manual.id}: {manual.title} ---")
        markdown = buscar_manual_com_docling(manual.id)
        if markdown:
            resultados.append({
                'id': manual.id,
                'title': manual.title,
                'url': manual.url,
                'markdown': markdown
            })
    
    print(f"\nConversão concluída! {len(resultados)} manuais convertidos com sucesso.")
    return resultados

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Converter manual específico
        manual_id = int(sys.argv[1])
        buscar_manual_com_docling(manual_id)
    else:
        # Converter todos os manuais
        converter_todos_manuais()