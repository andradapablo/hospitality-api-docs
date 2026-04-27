import json
import argparse
from pathlib import Path


PRIMITIVE_MAP = {
    "string": "pl.Utf8",
    "integer": "pl.Int64",
    "number": "pl.Float64",
    "boolean": "pl.Boolean",
}


def build_schema(swagger: dict, root_name: str):
    definitions = swagger.get("definitions") or swagger.get("components", {}).get("schemas", {})
    visited = set()

    def resolve_ref(ref: str):
        ref_name = ref.split("/")[-1]
        return ref_name, definitions.get(ref_name)

    def parse(schema: dict, level=0, is_root=False):
        indent = "    " * level
        next_indent = "    " * (level + 1)

        if not schema:
            return 'pl.Struct({"_dummy": pl.Utf8})'

        # $ref
        if "$ref" in schema:
            ref_name, ref_schema = resolve_ref(schema["$ref"])

            if ref_name in visited:
                return 'pl.Struct({"_ref": pl.Utf8})'

            visited.add(ref_name)
            result = parse(ref_schema, level)
            visited.remove(ref_name)
            return result

        schema_type = schema.get("type")

        # object
        if schema_type == "object" or "properties" in schema:
            props = schema.get("properties", {})

            if not props:
                return 'pl.Struct({"_dummy": pl.Utf8})'

            lines = ["{"] if is_root else ["pl.Struct({"]

            for k, v in props.items():
                parsed = parse(v, level + 1)
                lines.append(f'{next_indent}"{k}": {parsed},')

            if is_root:
                lines.append(f"{indent}}}")
            else:
                lines.append(f"{indent}}})")

            return "\n".join(lines)

        # array
        if schema_type == "array":
            items = schema.get("items", {})
            parsed_items = parse(items, level + 1)

            return f"""pl.List(
{next_indent}{parsed_items}
{indent})"""

        # primitives
        if schema_type == "string":
            fmt = schema.get("format")
            if fmt == "date":
                return "pl.Date"
            if fmt in ("date-time", "datetime"):
                return "pl.Datetime"
            return "pl.String"

        if schema_type in PRIMITIVE_MAP:
            return PRIMITIVE_MAP[schema_type]

        return "pl.String"

    root_schema = definitions.get(root_name)
    if not root_schema:
        raise ValueError(f"Schema '{root_name}' no encontrado en definitions")

    return parse(root_schema, level=1, is_root=True)

def generate_file(schema_str: str, output_file: Path):
    output_file.parent.mkdir(parents=True, exist_ok=True)
    classname = "".join(palabra.capitalize() for palabra in output_file.stem.split("_"))
    content = f"""import polars as pl
from utils.schemas.baseschema import AbstractSchema

class {classname}Strategy(AbstractSchema):
# AUTO-GENERATED FILE - DO NOT EDIT
    DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S.%f"

    name = "{classname}"
    schema = {schema_str}
"""

    output_file.write_text(content, encoding="utf-8")

def main():
    parser = argparse.ArgumentParser(description="Generate Polars schema from Swagger")

    parser.add_argument("--input-path", required=False, help="Directorio donde está el swagger", default="rest-api-specs/property")
    parser.add_argument("--input-file", required=True, help="Nombre del archivo swagger.json")
    parser.add_argument("--schema-name", required=True, help="Nombre del schema (ej: reservationsInformationType)")
    parser.add_argument("--output-file", required=True, help="Archivo de salida (.py)")
    
    args = parser.parse_args()

    input_file = Path(args.input_path) / args.input_file
    output_file = Path(args.output_file)

    with open(input_file, "r", encoding="utf-8") as f:
        swagger = json.load(f)

    schema_str = build_schema(swagger, args.schema_name)

    generate_file(schema_str, output_file)

    print(f"✅ Schema generado en: {output_file}")


if __name__ == "__main__":
    main()