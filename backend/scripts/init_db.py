"""Create all tables. Run once (or after a schema change) with:
    python scripts/init_db.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.base import Base, engine
from app.db import models  # noqa: F401  (registers the models on Base.metadata)


def main():
    Base.metadata.create_all(engine)
    print(f"Tables created: {list(Base.metadata.tables.keys())}")


if __name__ == "__main__":
    main()
