"""Serve o build local com a biblioteca padrão. Não é o backend da Valyra."""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DIST = Path(__file__).resolve().parents[1] / 'apps' / 'web' / 'dist'


class PreviewHandler(SimpleHTTPRequestHandler):
    def list_directory(self, path):
        # A prévia existe para os arquivos compilados, não para navegar no repositório.
        self.send_error(404)
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=4173)
    args = parser.parse_args()
    if not (DIST / 'index.html').is_file():
        parser.error('Build ausente. Execute npm run build na raiz primeiro.')
    handler = partial(PreviewHandler, directory=str(DIST))
    # Restrito ao computador local. Publicação HTTPS usa hospedagem estática, não este servidor.
    with ThreadingHTTPServer(('127.0.0.1', args.port), handler) as server:
        print(f'Valyra local: http://127.0.0.1:{args.port}', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print('\nPrévia encerrada.')


if __name__ == '__main__':
    main()
