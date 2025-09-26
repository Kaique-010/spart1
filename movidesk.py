import requests
from dotenv import load_dotenv
import os
import time
import datetime
import calendar
import json

# Carrega as variáveis de ambiente
load_dotenv()

MOVIDESK_API_URL = os.getenv("MOVIDESK_API_URL")
MOVIDESK_API_KEY = os.getenv("MOVIDESK_API_KEY")

dados_para_finetuning = []
TAMANHO_PAGINA = 100 # Vamos buscar de 100 em 100

print("--- INICIANDO BUSCA DE TICKETS (ESTRATÉGIA FINAL V3: PAGINAÇÃO MANUAL) ---")

# Define o período de busca
ano_inicial = 2020
ano_atual = datetime.date.today().year
mes_atual = datetime.date.today().month

for ano in range(ano_inicial, ano_atual + 1):
    limite_mes = mes_atual if ano == ano_atual else 12
    
    for mes in range(1, limite_mes + 1):
        primeiro_dia = f"{ano}-{mes:02d}-01T00:00:00.00z"
        ultimo_dia_num = calendar.monthrange(ano, mes)[1]
        ultimo_dia = f"{ano}-{mes:02d}-{ultimo_dia_num}T23:59:59.00z"

        print(f"\nBuscando tickets para o período de {mes:02d}/{ano}...")

        filtro_completo = (
            f"(createdDate ge {primeiro_dia} and createdDate le {ultimo_dia}) and "
            f"(status eq 'Novo' or status eq 'Em atendimento' or status eq 'Pausado' or "
            f"status eq 'Resolvido' or status eq 'Fechado' or status eq 'Cancelado')"
        )
        
        skip = 0 # Contador para pular os tickets já vistos
        while True: # Loop infinito para a paginação manual
            print(f"   -> Buscando página (pulando {skip} tickets)...")
            
            url_lista_tickets = (
                f"{MOVIDESK_API_URL}tickets?token={MOVIDESK_API_KEY}&"
                f"$select=id,subject&$top={TAMANHO_PAGINA}&$skip={skip}&$filter={filtro_completo}"
            )

            try:
                response_lista = requests.get(url_lista_tickets, timeout=45)
                response_lista.raise_for_status()

                lista_tkts = response_lista.json()
                
                if not lista_tkts:
                    print("      -> Fim dos tickets para este mês.")
                    break # Sai do loop 'while True' se não vierem mais tickets

                print(f"      -> Página com {len(lista_tkts)} tickets recebida. Verificando um por um...")

                for tkt in lista_tkts:
                    id_do_tkt = tkt['id']
                    
                    url_detalhes = f"{MOVIDESK_API_URL}tickets?token={MOVIDESK_API_KEY}&id={id_do_tkt}"
                    detalhes_tkt_response = requests.get(url_detalhes, timeout=45)
                    
                    if detalhes_tkt_response.status_code == 200:
                        dados_tkt = detalhes_tkt_response.json()
                        conversa_formatada = ""
                        contem_chat = False
                        if dados_tkt.get('actions'):
                            for acao in dados_tkt['actions']:
                                if acao.get('origin') in [3, 5, 6]:
                                    contem_chat = True
                                    autor = "Cliente" if acao.get('createdBy', {}).get('personType') == 3 else "Agente"
                                    mensagem = acao.get('description', '')
                                    if mensagem:
                                        conversa_formatada += f"{autor}: {mensagem}\n"
                        
                        if contem_chat and conversa_formatada:
                            print(f"         -> Encontrada conversa de CHAT no ticket {id_do_tkt}!")
                            dados_para_finetuning.append({
                                'id_ticket': id_do_tkt,
                                'assunto': dados_tkt.get('subject', 'Sem Assunto'),
                                'dialogo_completo': conversa_formatada.strip()
                            })
                            if len(dados_para_finetuning) % 20 == 0:
                                print(f"            -> {len(dados_para_finetuning)} conversas de chat extraídas no total...")

                # Se a página veio cheia, preparamos para buscar a próxima
                if len(lista_tkts) < TAMANHO_PAGINA:
                    print("      -> Última página do mês processada.")
                    break # Sai do loop 'while True' pois não há mais páginas
                else:
                    skip += TAMANHO_PAGINA # Incrementa o contador para pular para a próxima página

            except requests.exceptions.RequestException as e:
                print(f"      ❌ Erro de conexão: {e}. Tentando novamente em 10 segundos...")
                time.sleep(10)

print("\n" + "="*50)
print("--- Processamento Concluído ---")
print(f"Total de conversas de chat extraídas: {len(dados_para_finetuning)}")

if dados_para_finetuning:
    nome_do_arquivo = 'conversas_movidesk_completo.json'
    with open(nome_do_arquivo, 'w', encoding='utf-8') as f:
        json.dump(dados_para_finetuning, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Dados salvos com sucesso no arquivo: {nome_do_arquivo}")