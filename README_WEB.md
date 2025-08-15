# Sistema de Inserção de QR Code em PDF - Versão Web

## 🌟 Sobre o Projeto

Esta é uma aplicação web completa que replica todas as funcionalidades do sistema desktop original de inserção de QR Code em PDF. A aplicação permite carregar PDFs, posicionar QR codes interativamente, processar arquivos em lote e muito mais.

## ✨ Funcionalidades

### 📄 Gerenciamento de PDFs
- **Carregamento individual** de arquivos PDF
- **Carregamento em lote** de múltiplos PDFs
- **Visualização interativa** com navegação entre páginas
- **Renderização em alta qualidade** das páginas

### 🖼 Gerenciamento de QR Codes
- **Carregamento individual** de imagens QR
- **Carregamento em lote** de múltiplos QR codes
- **Extração automática** de QR codes de PDFs existentes
- **Matching automático** por nome do aluno

### 🎯 Posicionamento Interativo
- **Clique para posicionar** QR codes nas páginas
- **Controle de tamanho** ajustável (10% a 100% do menor lado)
- **Preview visual** em tempo real
- **Remoção** de QR codes posicionados

### 🔄 Processamento em Lote
- **Processamento automático** de múltiplos PDFs
- **Matching inteligente** entre PDFs e QR codes
- **Extração de nomes** dos PDFs para identificação
- **Geração de ZIP** com todos os arquivos processados

### 💾 Salvamento
- **Download individual** de PDFs com QR inserido
- **Download em lote** como arquivo ZIP
- **Preservação da qualidade** original dos documentos

## 🚀 Como Usar

### 📦 Repositório GitHub
O projeto está disponível em: **https://github.com/carlospiquet2023/qr_diplo**

### Instalação Local

#### 🚀 Primeira instalação (configuração inicial):

1. **Clone o repositório**:
   ```bash
   git clone https://github.com/carlospiquet2023/qr_diplo.git
   cd qr_diplo
   ```

2. **Crie um ambiente virtual**:
   ```bash
   python -m venv .venv
   ```

3. **Ative o ambiente virtual**:
   ```bash
   # Windows (PowerShell)
   .venv\Scripts\Activate.ps1
   
   # Linux/Mac
   source .venv/bin/activate
   ```

4. **Instale as dependências**:
   ```bash
   cd sistema_qr_web
   pip install -r requirements.txt
   ```

5. **Execute a aplicação**:
   ```bash
   python src/main.py
   ```

6. **Acesse no navegador**:
   ```
   http://localhost:5000
   ```

#### 🔄 Para execuções posteriores (projeto já configurado):

**Método rápido (comando único):**
```bash
cd "caminho/para/qr_diplo/sistema_qr_web" ; & "../.venv/Scripts/python.exe" src/main.py
```

**Método passo a passo:**
```bash
# 1. Navegue para o diretório do projeto
cd caminho/para/qr_diplo

# 2. Ative o ambiente virtual
.venv\Scripts\Activate.ps1

# 3. Entre no diretório da aplicação
cd sistema_qr_web

# 4. Execute a aplicação
python src/main.py

# 5. Acesse no navegador: http://localhost:5000
```

#### ⚠️ Observações importantes:
- **Não precisa** criar ambiente virtual novamente
- **Não precisa** instalar dependências novamente
- Para parar o servidor: pressione `Ctrl+C`
- O servidor roda em modo debug (mudanças são aplicadas automaticamente)

## 📋 Dependências

- **Flask** - Framework web
- **Flask-CORS** - Suporte a CORS
- **PyMuPDF** - Manipulação de PDFs
- **Pillow** - Processamento de imagens
- **OpenCV** - Detecção de QR codes
- **NumPy** - Operações numéricas

## 🎨 Interface

A aplicação possui uma interface moderna e responsiva com:
- **Design gradiente** profissional
- **Animações suaves** e micro-interações
- **Layout responsivo** para desktop e mobile
- **Feedback visual** em tempo real
- **Log de operações** detalhado

## 📖 Como Usar o Sistema

### 🔧 1. Inicializando a Aplicação

1. **Acesse a aplicação** em http://localhost:5000 após executar o servidor
2. **Aguarde o carregamento** da interface web
3. **Verifique se todas as seções** estão visíveis (Upload PDF, Upload QR, Visualização)

### 📄 2. Carregando PDFs

**Opção A - Upload Individual:**
1. Clique em **"Carregar PDF"**
2. Selecione o arquivo PDF desejado
3. Aguarde o processamento e visualização

**Opção B - Upload em Lote:**
1. Clique em **"Carregar PDFs em Lote"**
2. Selecione múltiplos arquivos PDF
3. Aguarde o processamento de todos os arquivos

### 🖼 3. Carregando QR Codes

**Opção A - Upload Individual:**
1. Clique em **"Carregar QR Code"**
2. Selecione a imagem do QR code (PNG, JPG, JPEG)
3. O QR será adicionado à lista disponível

**Opção B - Upload em Lote:**
1. Clique em **"Carregar QRs em Lote"**
2. Selecione múltiplas imagens de QR codes
3. Todos os QRs serão processados automaticamente

**Opção C - Extrair de PDFs:**
1. Clique em **"Extrair QRs de PDFs"**
2. Selecione PDFs que já contêm QR codes
3. O sistema extrairá automaticamente os QRs encontrados

### 🎯 4. Posicionando QR Codes

1. **Selecione um PDF** na área de visualização
2. **Navegue pelas páginas** usando os controles de página
3. **Clique na posição desejada** na página para posicionar o QR
4. **Ajuste o tamanho** usando o controle deslizante (10% a 100%)
5. **Visualize o preview** em tempo real
6. **Para remover**: clique novamente na posição do QR

### ⚙️ 5. Processamento em Lote

**Para matching automático:**
1. **Carregue PDFs em lote** (nomes devem conter identificadores dos alunos)
2. **Carregue QRs em lote** (nomes devem corresponder aos PDFs)
3. Clique em **"Processar em Lote"**
4. O sistema fará o matching automático por nome
5. **Aguarde o processamento** de todos os arquivos

### 💾 6. Salvando Resultados

**Download Individual:**
1. Após posicionar QRs, clique em **"Download PDF"**
2. O arquivo será baixado com o QR inserido

**Download em Lote:**
1. Após processamento em lote, clique em **"Download ZIP"**
2. Um arquivo ZIP será gerado com todos os PDFs processados

### 🔄 7. Workflow Recomendado

**Para uso individual:**
```
1. Carregar PDF → 2. Carregar QR → 3. Posicionar → 4. Download
```

**Para uso em lote:**
```
1. Carregar PDFs em lote → 2. Carregar QRs em lote → 3. Processar em lote → 4. Download ZIP
```

**Para extração de QRs existentes:**
```
1. Extrair QRs de PDFs → 2. Usar QRs extraídos → 3. Aplicar em novos PDFs
```

### 💡 8. Dicas Importantes

- **Nomenclatura**: Para matching automático, use nomes consistentes nos arquivos
- **Qualidade**: QR codes devem ter boa resolução para melhor resultado
- **Tamanho**: Ajuste o tamanho do QR conforme necessidade (recomendado: 20-30%)
- **Posição**: Escolha posições que não interfiram no conteúdo principal
- **Teste**: Sempre teste o QR code final para garantir que está funcionando

### ⚠️ 9. Limitações

- **Tamanho máximo**: 50MB por arquivo
- **Formatos suportados**: PDF (para documentos), PNG/JPG/JPEG (para QRs)
- **Navegadores**: Funciona melhor em Chrome, Firefox e Edge modernos
- **JavaScript**: Deve estar habilitado no navegador

## 🔧 Arquitetura

### Backend (Flask)
- **API RESTful** para todas as operações
- **Upload de arquivos** com validação
- **Processamento assíncrono** de PDFs
- **Geração de base64** para transferência

### Frontend (HTML/CSS/JS)
- **Interface SPA** (Single Page Application)
- **Drag & Drop** para upload de arquivos
- **Canvas interativo** para posicionamento
- **Estado global** da aplicação

## 📁 Estrutura do Projeto

```
sistema_qr_web/
├── src/
│   ├── main.py              # Aplicação Flask principal
│   ├── routes/
│   │   └── pdf_qr.py        # Rotas da API
│   ├── static/
│   │   ├── index.html       # Interface principal
│   │   └── app.js           # Lógica JavaScript
│   └── models/              # Modelos de dados
└── requirements.txt         # Dependências
```

## 🌐 Deploy

Para deploy em produção, recomenda-se:
- **Gunicorn** como servidor WSGI
- **Nginx** como proxy reverso
- **Docker** para containerização
- **SSL/HTTPS** para segurança

## 🔒 Segurança

- **Validação de tipos** de arquivo
- **Limite de tamanho** de upload (50MB)
- **Sanitização** de nomes de arquivo
- **CORS configurado** adequadamente

## 🐛 Solução de Problemas

### Erro de dependências
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Erro de porta ocupada
```bash
# Mude a porta no main.py
app.run(host='0.0.0.0', port=5001, debug=True)
```

### Problemas com OpenCV
```bash
# Ubuntu/Debian
sudo apt-get install python3-opencv

# Windows
pip install opencv-python-headless
```

## 📞 Suporte

Para dúvidas ou problemas:
1. Verifique os logs no console do navegador
2. Consulte o log da aplicação Flask
3. Verifique se todas as dependências estão instaladas

## 🎉 Conclusão

Esta aplicação web mantém 100% das funcionalidades do sistema desktop original, oferecendo uma experiência moderna e acessível via navegador. Todas as operações são realizadas de forma intuitiva e eficiente, com feedback visual constante para o usuário.

