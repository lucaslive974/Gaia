# Gaia — Extrator Inteligente de PDFs (CLI)

O **Gaia** é uma ferramenta de linha de comando (CLI) projetada para extrair informações estruturadas de notificações de infrações de trânsito em formato PDF. Ele foi estruturado para suportar fluxos de extração complexos, combinando leitura nativa rápida e reconhecimento óptico de caracteres (OCR) robusto de forma modular e resiliente.

---

## 🚀 Funcionalidades Principais

* **Pipeline de Extração Híbrida (Native + OCR)**:
  * O sistema tenta processar a página nativamente de forma ultra-rápida (via `pypdf`).
  * Caso a página seja um PDF escaneado (imagem) ou falhe na validação de campos obrigatórios, o Gaia realiza o fallback automaticamente para OCR (via `Tesseract OCR` e `pdf2image`) **apenas para aquela página específica**.
* **Interface de Terminal (TUI) Dinâmica**:
  * Renderização dinâmica em tempo real (via `rich.live`).
  * Painel consolidado contendo contadores de arquivos processados, páginas lidas de forma nativa vs. OCR e falhas.
  * Barra de progresso visual com estimativa numérica de tempo restante (**ETA**).
* **Cancelamento Gracioso**:
  * Suporta interrupção pelo usuário pressionando as teclas `ESC` ou `Ctrl+C` a qualquer momento, fechando conexões e restaurando o terminal de forma segura.
* **Log de Erros Detalhado**:
  * Páginas que falham na extração ou validação de campos obrigatórios são registradas no arquivo `gaia_errors.log` contendo os dados extraídos parcialmente e o texto completo da página para depuração posterior.
* **Saída Estruturada**:
  * Todos os registros validados são exportados para um arquivo CSV unificado (`output.csv`).

---

## 📁 Estrutura de Arquivos do Projeto

```text
Gaia/
├── config/
│   └── settings.py          # Configurações globais e caminhos padrão
├── core/
│   ├── csv_writer.py        # Gravação incremental e segura no arquivo CSV
│   ├── extractor.py         # Motores de extração (Nativo, OCR, Fallback)
│   ├── observer.py          # Interface observadora para progresso
│   ├── ocr_parser.py        # Regex KVP (Key-Value Pair) e validação de páginas
│   ├── shell_manager.py     # Orquestrador principal do ciclo de vida da CLI
│   └── terminal_ui.py       # Gerenciador de interface rica (TUI) e teclado
├── main.py                  # Ponto de entrada da aplicação (argparse)
├── requirements.txt         # Dependências do Python
├── tests/                   # Suíte de testes unitários e de integração
└── tools/
    └── linux/
        └── run_tests.sh     # Script utilitário para execução da suíte de testes
```

---

## 🛠️ Requisitos e Instalação

### Pré-requisitos
1. **Python 3.10+**
2. **Tesseract OCR**: Necessário para a extração em PDFs que contêm imagens escaneadas.
   * No Debian/Ubuntu:
     ```bash
     sudo apt update
     sudo apt install tesseract-ocr tesseract-ocr-por
     ```
3. **Poppler**: Requisito do `pdf2image` para converter páginas de PDF em imagem.
   * No Debian/Ubuntu:
     ```bash
     sudo apt install poppler-utils
     ```

### Configuração do Ambiente

1. Clone o repositório ou navegue até a pasta do projeto:
   ```bash
   cd Trabalho/Gaia
   ```

2. Crie e ative o ambiente virtual:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

---

## 💻 Como Usar

A CLI do Gaia possui interface em português e aceita argumentos para configurar os caminhos de entrada e saída.

```bash
python main.py <diretorio_de_entrada> [opções]
```

### Argumentos:
* `<diretorio_de_entrada>`: Caminho do diretório contendo os arquivos PDF a serem processados. (Obrigatório)

### Opções:
* `-o`, `--output` `<caminho_csv>`: Caminho do arquivo CSV de saída (Padrão: `./output.csv`).
* `-t`, `--traineddata` `<caminho_traineddata>`: Caminho da pasta contendo os dados de treinamento do Tesseract (Padrão: `./traineddata`).

### Exemplos de Execução:

* **Execução básica**:
  ```bash
  python main.py /home/lucaslima/Documents/Multas
  ```

* **Definindo arquivo de saída personalizado**:
  ```bash
  python main.py /home/lucaslima/Documents/Multas -o /home/lucaslima/Documents/resultado.csv
  ```

---

## 🧪 Executando Testes

A suíte de testes valida a lógica do fluxo da CLI, os extratores de texto, o comportamento do observer e do parser KVP.

Para executar todos os testes, utilize o script utilitário:
```bash
./tools/linux/run_tests.sh
```
