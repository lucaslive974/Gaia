import argparse
from config import settings
from core.terminal_ui import run_with_ui


def main():
    parser = argparse.ArgumentParser(
        description="Gaia/Atlas PDF Extractor - Ferramenta CLI de extração inteligente de dados de PDFs."
    )
    parser.add_argument(
        "input_dir",
        type=str,
        help="Caminho do diretório contendo os arquivos PDF a serem processados.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=settings["OUTPUT_CSV"],
        help=f"Caminho do arquivo CSV de saída (Padrão: {settings['OUTPUT_CSV']}).",
    )
    parser.add_argument(
        "-r",
        "--resume",
        action="store_true",
        help="Retoma o processamento a partir do último arquivo concluído com sucesso.",
    )

    args = parser.parse_args()
    settings.parse_cmd_args(args)

    run_with_ui(settings)


if __name__ == "__main__":
    main()

