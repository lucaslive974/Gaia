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
        nargs="?",
        default=None,
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
        "--resume",
        action="store_true",
        help="Retoma o processamento a partir do último arquivo concluído com sucesso.",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Busca arquivos PDF recursivamente nos subdiretórios.",
    )
    parser.add_argument(
        "-g",
        "--regex",
        type=str,
        default=None,
        help="Caminho do arquivo JSON contendo as regras regex customizadas.",
    )
    parser.add_argument(
        "-t",
        "--test",
        type=str,
        default=None,
        metavar="FILE_PATH",
        help="Testa as regras de regex na primeira página do arquivo PDF fornecido.",
    )

    args = parser.parse_args()

    try:
        settings.parse_cmd_args(args)
    except ValueError as e:
        parser.error(str(e))

    if settings.TEST_FILE:
        from core.terminal_ui import run_test_mode
        run_test_mode(settings)
    else:
        run_with_ui(settings)


if __name__ == "__main__":
    main()


