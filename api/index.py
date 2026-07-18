import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('VERCEL', '1')

from app import create_app

app = create_app('production')

if __name__ == '__main__':
    app.run()
