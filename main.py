import argparse
from config.settings import Settings
from core.shell_manager import ShellManager


def main():
    settings = Settings()
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
        "-t",
        "--traineddata",
        type=str,
        default=settings["TRAINED_DATA_DIR"],
        help=f"Caminho da pasta traineddata do Tesseract (Padrão: {settings['TRAINED_DATA_DIR']}).",
    )

    parser.add_argument(
        "-m",
        "--mode",
        type=str,
        default=settings["MODE"],
        help=f"Modo de extração (Padrão: {settings['MODE']})",
    )

    args = parser.parse_args()
    settings.parse_cmd_args(args)

    shell = ShellManager()
    shell.run(settings)


if __name__ == "__main__":
    main()
