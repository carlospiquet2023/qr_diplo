#!/usr/bin/env python3
"""
Script para debugar extração de nomes de PDFs
"""
import fitz  # PyMuPDF
import sys
import re
import unicodedata

def limpar_nome_arquivo(nome):
    """Remove acentos e caracteres especiais do nome do arquivo"""
    nome = unicodedata.normalize('NFD', nome)
    nome = ''.join(char for char in nome if unicodedata.category(char) != 'Mn')
    nome = re.sub(r'[^\w\s-]', '', nome)
    nome = re.sub(r'[-\s]+', '_', nome)
    return nome.strip('_')

def debug_extrair_nome_do_pdf(pdf_path):
    """Debuga a extração de nome do PDF"""
    try:
        print(f"Analisando PDF: {pdf_path}")
        
        # Abre o PDF
        doc = fitz.open(pdf_path)
        page = doc[0]
        text = page.get_text()
        doc.close()
        
        print("=== TEXTO COMPLETO DO PDF ===")
        print(text)
        print("=" * 50)
        
        # Primeiro tenta o padrão "Nome do aluno:"
        match = re.search(r'Nome do aluno:\s*(.+)', text, re.IGNORECASE)
        if match:
            nome = match.group(1).strip()
            print(f"Padrão 'Nome do aluno:' encontrado: {nome}")
            return limpar_nome_arquivo(nome)
        
        print("Padrão 'Nome do aluno:' não encontrado")
        print("Tentando identificar nomes próprios...")
        
        # Para diplomas, procura por padrões de nomes próprios
        lines = text.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            print(f"Linha {i}: '{line}'")
            
            # Ignora linhas muito curtas ou muito longas
            if len(line) < 5 or len(line) > 50:
                print(f"  -> Ignorada (tamanho: {len(line)})")
                continue
            
            # Procura por padrão de nome (palavras com primeira letra maiúscula)
            words = line.split()
            if len(words) >= 2:
                print(f"  -> Palavras: {words}")
                
                # Verifica se todas as palavras começam com maiúscula (exceto conectores)
                conectores = ['de', 'da', 'do', 'dos', 'das', 'e']
                nome_valido = True
                for word in words:
                    if word.lower() not in conectores and not word[0].isupper():
                        nome_valido = False
                        print(f"    -> Palavra inválida: {word}")
                        break
                
                if nome_valido:
                    print(f"  -> Nome válido encontrado!")
                    
                    # Verifica se não contém números ou símbolos estranhos
                    if not re.search(r'[0-9@#$%^&*()_+={}|\\:";\'<>?,.\/]', line):
                        print(f"  -> Sem números/símbolos")
                        
                        # Verifica se não é uma palavra comum de diploma
                        palavras_ignorar = ['diploma', 'certificado', 'curso', 'universidade', 
                                          'faculdade', 'instituto', 'graduação', 'bacharelado',
                                          'licenciatura', 'tecnólogo', 'especialização', 'mestrado',
                                          'doutorado', 'pós-graduação', 'conclusão', 'formatura']
                        
                        if not any(palavra in line.lower() for palavra in palavras_ignorar):
                            nome = limpar_nome_arquivo(line)
                            print(f"NOME EXTRAÍDO: {nome}")
                            return nome
                        else:
                            print(f"  -> Contém palavras de diploma")
                    else:
                        print(f"  -> Contém números/símbolos")
                else:
                    print(f"  -> Nome inválido")
        
        print("Nenhum nome encontrado")
        return None
        
    except Exception as e:
        print(f"Erro ao extrair nome do PDF: {e}")
        return None

if __name__ == "__main__":
    # Testa com um PDF específico
    pdf_path = r"c:\Users\pique\OneDrive\Área de Trabalho\qr\Alicia_Araujo.pdf"
    resultado = debug_extrair_nome_do_pdf(pdf_path)
    print(f"\nResultado final: {resultado}")
