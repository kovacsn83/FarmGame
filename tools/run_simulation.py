"""Parancssori belépési pont az ötéves gazdasági szimulációhoz."""

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from simulation import DEFAULT_SIMULATION_SEED, run_simulation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=5)
    parser.add_argument("--seed", type=int, default=DEFAULT_SIMULATION_SEED)
    parser.add_argument("--report-dir", default=str(ROOT / "reports"))
    parser.add_argument(
        "--verbose", action="store_true",
        help="Megjeleníti a játékrendszerek részletes eseménynaplóját.",
    )
    args = parser.parse_args()
    result = run_simulation(
        args.years, args.seed, args.report_dir, verbose=args.verbose,
    )
    print("Szimuláció: SIKERES")
    print(f"Feldolgozott hetek: {result['weeks_processed']}")
    print(f"Végső egyenleg: ${result['final_money']:.2f}")
    print(f"Futási idő: {result['runtime_seconds']:.3f} mp")
    print(f"Invariánshibák: {len(result['invariant_errors'])}")
    print(f"Markdown riport: {result['report_paths']['markdown']}")
    print(f"JSON riport: {result['report_paths']['json']}")


if __name__ == "__main__":
    main()
