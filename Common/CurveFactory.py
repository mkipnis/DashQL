# Copyright (c) Mike Kipnis - DashQL

import json
import argparse
from datetime import date

import QuantLib as ql
from Common.Utils import CurveUtils


def main():
    parser = argparse.ArgumentParser(description="Curve Factory")
    parser.add_argument('--json_file', required=True)
    args = parser.parse_args()

    # Read JSON file
    with open(args.json_file, "r") as f:
        data = json.load(f)

    curve_dict = {}
    for curve in data:
        curve_name = curve['Name']
        print(f"Transforming : {curve_name}")
        transformed_curve = CurveUtils.transform_curve_components(curve)
        curve_dict[curve_name] = transformed_curve

    print(curve_dict)

if __name__ == "__main__":
    main()
