# 📄 Sistema de QR Code para PDFs - Versão Web

[![Status](https://img.shields.io/badge/Status-Ativo-success)](https://github.com/carlospiquet2023/qr_diplo)
[![Version](https://img.shields.io/badge/Version-2.0-blue)](https://github.com/carlospiquet2023/qr_diplo)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

> **Sistema completo para extração e inserção de códigos QR em documentos PDF com processamento em lote e posicionamento unificado.**

## 🌟 **Visão Geral**

Este sistema permite extrair códigos QR de documentos PDF existentes (como diplomas já assinados) e inseri-los em novos documentos PDF (como diplomas em branco), mantendo a correspondência automática por nome do aluno e posicionamento unificado.

### ✨ **Principais Funcionalidades**

- 🎯 **QR Individual**: Cada aluno recebe seu próprio código QR único
- 📍 **Posição Unificada**: Todos os QRs na mesma posição definida visualmente  
- 🔄 **Processamento em Lote**: Processa múltiplos documentos automaticamente
- 🧠 **Matching Inteligente**: Associa QRs e PDFs automaticamente por nome
- 📦 **Download ZIP**: Baixa todos os documentos processados
- 🖥️ **Interface Web**: Funciona em qualquer navegador moderno

## 🚀 **Instalação e Uso**

### **📋 Pré-requisitos**
- Python 3.8+
- Navegador web moderno
- Git (opcional)

### **⚡ Instalação Rápida**

```bash
# 1. Clone o repositório
git clone https://github.com/carlospiquet2023/qr_diplo.git
cd qr_diplo

# 2. Crie e ative o ambiente virtual
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac  
source .venv/bin/activate

# 3. Instale as dependências
cd sistema_qr_web
pip install -r requirements.txt

# 4. Execute o sistema
python src/main.py

# 5. Acesse no navegador
# http://localhost:5000
```

### **🔄 Execuções Posteriores**

```bash
# Comando único (Windows)
cd "caminho/para/qr_diplo" && .venv\Scripts\python.exe sistema_qr_web\src\main.py

# Ou passo a passo
cd qr_diplo
.venv\Scripts\activate
cd sistema_qr_web  
python src/main.py
```

## 📖 **Como Usar**

### **🎯 Fluxo Principal**

1. **📄 Upload dos PDFs**: Carregue os documentos que receberão os QRs
2. **🖼️ Extração de QRs**: Extraia QRs de documentos existentes  
3. **📍 Posicionamento**: Clique no primeiro documento para definir a posição
4. **⚙️ Processamento**: Execute o processamento em lote
5. **📦 Download**: Baixe o ZIP com todos os documentos processados

### **📋 Passo a Passo Detalhado**

#### **1. Carregar Documentos**
- Clique em **"Carregar PDFs em Lote"**
- Selecione os documentos que receberão os QRs
- Aguarde o carregamento e preview

#### **2. Extrair QR Codes**  
- Clique em **"Extrair QR e Carregar"**
- Selecione documentos que já possuem QRs
- O sistema extrairá automaticamente os QRs individuais

#### **3. Definir Posição**
- Visualize o primeiro documento carregado
- **Clique onde deseja posicionar o QR**
- Ajuste o tamanho usando o slider (10-100%)
- Esta posição será aplicada a todos os documentos

#### **4. Processar em Lote**
- Clique em **"Processar em Lote"**  
- O sistema fará o matching automático por nome
- Cada documento receberá seu QR individual na posição definida

#### **5. Download dos Resultados**
- Clique em **"Download ZIP"** quando o processamento terminar
- Todos os documentos processados serão baixados em um arquivo ZIP

## 🔧 **Como Funciona o Sistema**

### **🧠 Matching Inteligente**

O sistema usa algoritmos avançados para associar QRs e PDFs:

```python
# Exemplo de matching
PDF: "Maria_Silva.pdf" → QR: "Maria Silva.png" ✅
PDF: "joao-santos.pdf" → QR: "João Santos.png" ✅  
PDF: "Ana_Costa.pdf" → QR: "ana costa.png" ✅
```

**Características do Matching:**
- Remove acentos e caracteres especiais
- Ignora diferenças de capitalização  
- Trata underscores, hífens e espaços como equivalentes
- Funciona mesmo com pequenas variações nos nomes

### **📍 Sistema de Posicionamento**

- **Posição Unificada**: Define uma vez, aplica a todos
- **Coordenadas Precisas**: Conversão exata entre interface e PDF
- **Escalamento Automático**: Mantém proporções em diferentes tamanhos de página
- **Preview em Tempo Real**: Visualiza antes de processar

## 🏗️ **Arquitetura Técnica**

### **Backend (Python/Flask)**
```
├── main.py              # Servidor Flask principal
├── routes/
│   └── pdf_qr.py        # API endpoints
├── models/
│   └── user.py          # Modelos de dados
└── static/              # Frontend
    ├── index.html       # Interface principal
    ├── app.js           # Lógica principal
    └── app_new_functions.js # Funções auxiliares
```

### **Tecnologias Utilizadas**
- **Flask** - Framework web backend
- **PyMuPDF** - Manipulação de documentos PDF
- **OpenCV** - Detecção e processamento de QR codes
- **Pillow** - Processamento de imagens
- **NumPy** - Operações matemáticas
- **JSZip** - Criação de arquivos ZIP no frontend

## 📊 **Logs e Debugging**

### **Logs do Sistema**
O sistema fornece logs detalhados durante o processamento:

```
✅ QR 'Maria Silva.png' mapeado para 'Maria Silva'
✅ Processando PDF: Maria_Silva.pdf  
✅ Nome extraído: 'Maria Silva'
✅ QR inserido em Maria_Silva.pdf
📦 Processamento concluído: 15 de 15 PDFs processados
```

### **Verificação de Problemas**
```bash
# Verificar dependências
pip list | grep -E "(flask|opencv|pymupdf|pillow)"

# Verificar logs em tempo real
# Acesse http://localhost:5000 e abra DevTools (F12)
```

## ⚠️ **Solução de Problemas Comuns**

### **🔴 "Nenhum PDF foi processado"**
- ✅ Verifique se os nomes dos arquivos correspondem
- ✅ Confirme que a posição do QR foi definida
- ✅ Verifique os logs no console do navegador

### **🔴 "QR Code não encontrado"**  
- ✅ Use QRs em boa resolução (PNG recomendado)
- ✅ Verifique se o QR está claramente visível no documento
- ✅ Tente aumentar a resolução da imagem

### **🔴 "Erro de matching"**
- ✅ Use nomes similares nos arquivos PDF e QR
- ✅ Evite caracteres especiais excessivos
- ✅ Prefira formato: "Nome_Sobrenome.pdf" / "Nome Sobrenome.png"

### **🔴 "Servidor não inicia"**
```bash
# Verificar se a porta está em uso
netstat -an | find "5000"

# Usar porta alternativa  
# Edite main.py: app.run(host='0.0.0.0', port=5001)
```

## 📈 **Atualizações Recentes**

### **🚀 Versão 2.0 (Atual)**
- ✅ Cada aluno recebe seu QR individual (correção crítica)
- ✅ Posicionamento unificado aprimorado
- ✅ Matching por nome de arquivo como fallback
- ✅ Extração de nomes melhorada (remove palavras incorretas)
- ✅ Logs mais detalhados para debugging
- ✅ Sistema de download ZIP funcional

### **📋 Versões Anteriores**
- **v1.2**: Interface web responsiva
- **v1.1**: Processamento em lote básico  
- **v1.0**: Sistema desktop original (Tkinter)

## 🤝 **Contribuição**

### **📝 Reportar Problemas**
- Use as [Issues do GitHub](https://github.com/carlospiquet2023/qr_diplo/issues)
- Inclua logs de erro e arquivos de exemplo
- Descreva o comportamento esperado vs. atual

### **🔧 Desenvolvimento**
```bash
# Fazer fork do repositório
git clone https://github.com/SEU_USUARIO/qr_diplo.git

# Criar branch para feature
git checkout -b nova-funcionalidade

# Fazer commit e push
git add .
git commit -m "✨ Nova funcionalidade: descrição"
git push origin nova-funcionalidade

# Abrir Pull Request
```

## 📄 **Licença**

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 📞 **Suporte e Contato**

- **🐛 Issues**: [GitHub Issues](https://github.com/carlospiquet2023/qr_diplo/issues)
- **📚 Documentação**: Este README + código comentado
- **🔄 Atualizações**: Acompanhe as releases no GitHub

---

## 🎯 **Status do Projeto**

- ✅ **Sistema Principal**: Funcional e testado
- ✅ **Interface Web**: Moderna e responsiva  
- ✅ **Processamento em Lote**: QRs individuais + posição unificada
- ✅ **Download ZIP**: Funcional
- ✅ **Matching Inteligente**: Robusto e flexível
- ✅ **Documentação**: Completa e atualizada

**🎉 O sistema está pronto para uso em produção!**

---

<div align="center">

**Desenvolvido para facilitar o processamento em lote de documentos com códigos QR**

[⭐ Star](https://github.com/carlospiquet2023/qr_diplo) • [🐛 Issues](https://github.com/carlospiquet2023/qr_diplo/issues) • [📝 Contribuir](https://github.com/carlospiquet2023/qr_diplo/pulls)

</div>
