import json
import math
import re
import sys
import uuid
from pathlib import Path


PART_RE = re.compile(
    r"PartDefinition\s+(\w+)\s*=\s*(\w+)\.addOrReplaceChild\(\s*\"([^\"]+)\"\s*,\s*CubeListBuilder\.create\(\)(.*?)\s*,\s*PartPose\.(offsetAndRotation|offset)\((.*?)\)\s*\)\s*;",
    re.DOTALL,
)

TEX_BOX_RE = re.compile(
    r"\.texOffs\(\s*([-\d]+)\s*,\s*([-\d]+)\s*\)\s*\.addBox\((.*?)\)\s*(?=\.texOffs|$)",
    re.DOTALL,
)

ROOT_Y = 24.0


def parse_numbers(raw: str) -> list[float]:
    return [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", raw)]


def rad_to_deg(value: float) -> float:
    return round(math.degrees(value), 6)


def round_list(values: list[float]) -> list[float]:
    return [round(v, 6) for v in values]


def to_blockbench_point(p: list[float]) -> list[float]:
    # Mirror X to match Blockbench java_block orientation, flip Y axis.
    return [-p[0], ROOT_Y - p[1], p[2]]


def normalize_box(a: list[float], b: list[float]) -> tuple[list[float], list[float]]:
    return (
        [min(a[0], b[0]), min(a[1], b[1]), min(a[2], b[2])],
        [max(a[0], b[0]), max(a[1], b[1]), max(a[2], b[2])],
    )


def build_faces(u: float, v: float, w: float, h: float, d: float) -> dict:
    # Minecraft/Blockbench box_uv layout
    return {
        "north": {"uv": [u + d, v + d, u + d + w, v + d + h], "texture": 0},
        "east": {"uv": [u, v + d, u + d, v + d + h], "texture": 0},
        "south": {"uv": [u + d + w + d, v + d, u + d + w + d + w, v + d + h], "texture": 0},
        "west": {"uv": [u + d + w, v + d, u + d + w + d, v + d + h], "texture": 0},
        "up": {"uv": [u + d + w, v + d, u + d, v], "texture": 0},
        "down": {"uv": [u + d + w + w, v, u + d + w, v + d], "texture": 0},
    }


def convert_java_model(input_file: str, output_file: str, model_name: str = "custom_model") -> tuple[int, int]:
    with open(input_file, "r", encoding="utf-8") as f:
        text = f.read()

    parts: dict[str, dict] = {}
    parse_order: list[str] = []

    for m in PART_RE.finditer(text):
        var_name, parent_var, node_name, builder_chain, pose_kind, pose_args = m.groups()
        pose_nums = parse_numbers(pose_args)

        if pose_kind == "offset":
            ox, oy, oz = pose_nums[:3]
            rx = ry = rz = 0.0
        else:
            ox, oy, oz, rx, ry, rz = pose_nums[:6]

        cubes = []
        for tb in TEX_BOX_RE.finditer(builder_chain):
            u = int(tb.group(1))
            v = int(tb.group(2))
            box_raw = tb.group(3)

            # Support:
            # 1) new CubeDeformation(-0.005F)
            # 2) CubeDeformation.NONE
            box_raw = re.sub(
                r"new\s+CubeDeformation\(\s*([-\d.]+)\s*[Ff]?\s*\)",
                r"\1",
                box_raw,
            ).replace("CubeDeformation.NONE", "0")

            vals = parse_numbers(box_raw)
            if len(vals) < 6:
                continue

            x, y, z, sx, sy, sz = vals[:6]
            inflate = vals[6] if len(vals) >= 7 else 0.0

            cubes.append(
                {
                    "uv": [u, v],
                    "from": [x - inflate, y - inflate, z - inflate],
                    "to": [x + sx + inflate, y + sy + inflate, z + sz + inflate],
                }
            )

        parts[var_name] = {
            "var": var_name,
            "name": node_name,
            "parent_var": parent_var,
            "origin": [ox, oy, oz],
            "rotation": [rad_to_deg(rx), rad_to_deg(ry), rad_to_deg(rz)],
            "cubes": cubes,
            "children": [],
            "uuid": str(uuid.uuid4()),
        }
        parse_order.append(var_name)

    for var_name, node in parts.items():
        parent_var = node["parent_var"]
        if parent_var in parts:
            parts[parent_var]["children"].append(var_name)

    world_origin_cache: dict[str, list[float]] = {}

    def get_world_origin(var_name: str) -> list[float]:
        cached = world_origin_cache.get(var_name)
        if cached is not None:
            return cached
        node = parts[var_name]
        ox, oy, oz = node["origin"]
        parent_var = node["parent_var"]
        if parent_var in parts:
            pox, poy, poz = get_world_origin(parent_var)
            world = [ox + pox, oy + poy, oz + poz]
        else:
            world = [ox, oy, oz]
        world_origin_cache[var_name] = world
        return world

    elements = []
    part_cube_uuid_map: dict[str, list[str]] = {}

    for var_name in parse_order:
        node = parts[var_name]
        world_origin = get_world_origin(var_name)
        cube_uuids = []
        for index, cube in enumerate(node["cubes"], start=1):
            eid = str(uuid.uuid4())
            cube_uuids.append(eid)
            element_name = node["name"] if len(node["cubes"]) == 1 else f"{node['name']}_{index}"

            from_java = [
                cube["from"][0] + world_origin[0],
                cube["from"][1] + world_origin[1],
                cube["from"][2] + world_origin[2],
            ]
            to_java = [
                cube["to"][0] + world_origin[0],
                cube["to"][1] + world_origin[1],
                cube["to"][2] + world_origin[2],
            ]
            from_bb, to_bb = normalize_box(to_blockbench_point(from_java), to_blockbench_point(to_java))
            from_pos = round_list(from_bb)
            to_pos = round_list(to_bb)

            w = to_pos[0] - from_pos[0]
            h = to_pos[1] - from_pos[1]
            d = to_pos[2] - from_pos[2]
            u, v = cube["uv"]

            elements.append(
                {
                    "name": element_name,
                    "box_uv": True,
                    "rescale": False,
                    "locked": False,
                    "from": from_pos,
                    "to": to_pos,
                    "autouv": 0,
                    "color": 0,
                    "origin": round_list(to_blockbench_point(world_origin)),
                    "faces": build_faces(u, v, w, h, d),
                    "type": "cube",
                    "uuid": eid,
                }
            )

        part_cube_uuid_map[var_name] = cube_uuids

    def build_outliner_node(var_name: str) -> dict:
        node = parts[var_name]
        out = {
            "name": node["name"],
            "origin": round_list(to_blockbench_point(node["origin"])),
            "color": 0,
            "uuid": node["uuid"],
            "export": True,
            "mirror_uv": False,
            "isOpen": True,
            "locked": False,
            "visibility": True,
            "autouv": 0,
            "children": [],
        }

        # Keep cube placement stable by not writing outliner rotation.
        out["children"].extend(part_cube_uuid_map[var_name])
        for child_var in node["children"]:
            out["children"].append(build_outliner_node(child_var))
        return out

    outliner = []
    for var_name in parse_order:
        if parts[var_name]["parent_var"] == "partdefinition":
            outliner.append(build_outliner_node(var_name))

    result = {
        "meta": {"format_version": "5.0", "model_format": "java_block", "box_uv": True},
        "name": model_name,
        "parent": "",
        "java_block_version": "1.21.11",
        "ambientocclusion": True,
        "front_gui_light": False,
        "visible_box": [1, 1, 0],
        "variable_placeholders": "",
        "multi_file_ruleset": "",
        "variable_placeholder_buttons": [],
        "unhandled_root_fields": {},
        "resolution": {"width": 128, "height": 128},
        "elements": elements,
        "outliner": outliner,
    }

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return len(parts), len(elements)


def launch_gui() -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox

    root = tk.Tk()
    root.title("Java Model -> Blockbench Converter")
    root.geometry("760x300")
    root.minsize(760, 300)

    input_var = tk.StringVar()
    output_var = tk.StringVar()
    model_var = tk.StringVar(value="custom_model")
    status_var = tk.StringVar(value="Ready")

    def pick_input() -> None:
        path = filedialog.askopenfilename(
            title="Select Java model file",
            filetypes=[("Java Files", "*.java"), ("All Files", "*.*")],
        )
        if not path:
            return
        input_var.set(path)
        if not output_var.get().strip():
            output_var.set(str(Path(path).with_suffix(".bbmodel")))

    def pick_output() -> None:
        path = filedialog.asksaveasfilename(
            title="Save output",
            defaultextension=".bbmodel",
            filetypes=[("Blockbench Model", "*.bbmodel"), ("JSON", "*.json"), ("All Files", "*.*")],
        )
        if path:
            output_var.set(path)

    def do_convert() -> None:
        input_path = input_var.get().strip()
        output_path = output_var.get().strip()
        model_name = model_var.get().strip() or "custom_model"

        if not input_path:
            messagebox.showwarning("Missing Input", "Please select a Java file.")
            return
        if not output_path:
            messagebox.showwarning("Missing Output", "Please select an output file.")
            return
        if not Path(input_path).exists():
            messagebox.showerror("Input Error", f"Input file not found:\n{input_path}")
            return

        try:
            parts_count, cubes_count = convert_java_model(input_path, output_path, model_name=model_name)
            status_var.set(f"Done: {output_path} (Parts: {parts_count}, Cubes: {cubes_count})")
            messagebox.showinfo(
                "Success",
                f"Converted successfully.\n\nOutput: {output_path}\nParts: {parts_count}\nCubes: {cubes_count}",
            )
        except Exception as exc:
            status_var.set("Failed")
            messagebox.showerror("Convert Failed", str(exc))

    frame = tk.Frame(root, padx=14, pady=14)
    frame.pack(fill="both", expand=True)

    tk.Label(frame, text="Input Java").grid(row=0, column=0, sticky="w")
    tk.Entry(frame, textvariable=input_var, width=78).grid(row=1, column=0, sticky="we", padx=(0, 8))
    tk.Button(frame, text="Browse", width=12, command=pick_input).grid(row=1, column=1, sticky="e")

    tk.Label(frame, text="Output (.bbmodel/.json)").grid(row=2, column=0, sticky="w", pady=(10, 0))
    tk.Entry(frame, textvariable=output_var, width=78).grid(row=3, column=0, sticky="we", padx=(0, 8))
    tk.Button(frame, text="Browse", width=12, command=pick_output).grid(row=3, column=1, sticky="e")

    tk.Label(frame, text="Model Name").grid(row=4, column=0, sticky="w", pady=(10, 0))
    tk.Entry(frame, textvariable=model_var, width=30).grid(row=5, column=0, sticky="w")

    tk.Button(frame, text="Convert", width=16, command=do_convert).grid(row=6, column=0, sticky="w", pady=(16, 0))
    tk.Label(frame, textvariable=status_var, fg="#2b6cb0").grid(row=7, column=0, sticky="w", pady=(12, 0))

    frame.columnconfigure(0, weight=1)
    root.mainloop()


def main() -> None:
    # GUI mode:
    #   python main.py
    #   python main.py --gui
    # CLI mode:
    #   python main.py <input.java> [output.bbmodel/json] [model_name]
    if len(sys.argv) == 1 or (len(sys.argv) >= 2 and sys.argv[1] == "--gui"):
        launch_gui()
        return

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else str(Path(input_file).with_suffix(".bbmodel"))
    model_name = sys.argv[3] if len(sys.argv) > 3 else "custom_model"

    parts_count, cubes_count = convert_java_model(input_file, output_file, model_name=model_name)
    print(f"Done: {output_file}")
    print(f"Parts: {parts_count}, Cubes: {cubes_count}")


if __name__ == "__main__":
    main()
