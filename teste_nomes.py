#!/usr/bin/env python3
"""
Script de teste para verificar extração de nomes e matching
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sistema_qr_web', 'src'))

from routes.pdf_qr import extrair_nome_do_pdf, limpar_nome_arquivo, normalizar_para_matching

def testar_extrair_nome():
    print("=== TESTE DE EXTRAÇÃO DE NOMES ===")
    
    # Testa com PDF de exemplo (se existir)
    pdf_path = r"c:\Users\pique\OneDrive\Área de Trabalho\qr\Alicia_Araujo.pdf"
    
    if os.path.exists(pdf_path):
        print(f"Testando com PDF: {pdf_path}")
        
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        nome_extraido = extrair_nome_do_pdf(pdf_bytes)
        print(f"Nome extraído: '{nome_extraido}'")
        
        if nome_extraido:
            nome_limpo = limpar_nome_arquivo(nome_extraido)
            nome_norm, nome_sem_esp = normalizar_para_matching(nome_extraido)
            
            print(f"Nome limpo: '{nome_limpo}'")
            print(f"Nome normalizado: '{nome_norm}'")
            print(f"Nome sem espaços: '{nome_sem_esp}'")
    else:
        print(f"PDF não encontrado: {pdf_path}")

def testar_matching():
    print("\n=== TESTE DE MATCHING ===")
    
    # Testa diferentes variações de nomes
    nomes_teste = [
        ("Alicia Araujo", ["Alícia_Araújo", "alicia araujo", "ALICIA ARAUJO"]),
        ("João da Silva", ["joao_da_silva", "João Silva", "Joao Silva"]),
        ("María José", ["maria jose", "Maria_Jose", "MARIA JOSE"])
    ]
    
    for nome_pdf, nomes_qr in nomes_teste:
        print(f"\nTestando nome do PDF: '{nome_pdf}'")
        nome_norm_pdf, nome_sem_esp_pdf = normalizar_para_matching(nome_pdf)
        
        for nome_qr in nomes_qr:
            nome_norm_qr, nome_sem_esp_qr = normalizar_para_matching(nome_qr)
            
            match_normalizado = nome_norm_pdf == nome_norm_qr
            match_sem_espacos = nome_sem_esp_pdf == nome_sem_esp_qr
            
            print(f"  QR: '{nome_qr}' -> Norm: {match_normalizado}, Sem espaços: {match_sem_espacos}")

if __name__ == "__main__":
    testar_extrair_nome()
    testar_matching()
