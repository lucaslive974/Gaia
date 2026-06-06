import argparse
import os
import json
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
        "-r",
        "--resume",
        action="store_true",
        help="Retoma o processamento a partir do último arquivo concluído com sucesso.",
    )

    args = parser.parse_args()

    if not args.input_dir:
        if args.resume:
            state_file_cwd = os.path.join(os.getcwd(), ".gaia_resume.json")
            if os.path.exists(state_file_cwd):
                try:
                    with open(state_file_cwd, "r", encoding="utf-8") as sf:
                        state_data = json.load(sf)
                        args.input_dir = state_data.get("input_dir")
                        state_output = state_data.get("output_file")
                        if state_output:
                            args.output = state_output
                except Exception:
                    pass
            if not args.input_dir:
                parser.error("Nenhum estado de retomada encontrado no diretório atual. É necessário especificar o 'input_dir'.")
        else:
            parser.error("o argumento posicional 'input_dir' é obrigatório a menos que --resume seja usado com um estado salvo.")

    settings.parse_cmd_args(args)

    run_with_ui(settings)


if __name__ == "__main__":
    main()

