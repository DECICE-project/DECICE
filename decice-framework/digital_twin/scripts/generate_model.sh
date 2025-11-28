#!/usr/bin/env bash
datamodel-codegen --input "configs/DT_json_schema.json" --input-file-type "jsonschema" --output "src/digital_twin/core/data_model.py" \
 --use-title-as-name --use-non-positive-negative-number-constrained-types --field-constraints 
