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
AXIS_PRESETS: dict[str, dict[str, bool]] = {
    "legacy": {"mirror_x": True, "flip_y": True, "flip_z": False},
    "no_mirror_x": {"mirror_x": False, "flip_y": True, "flip_z": False},
}
ROTATION_MODES = ("elements", "groups")
RIG_PRESETS = ("generic", "changed_oldrig")
EMBED_AXIS_PRESET = "legacy"
EMBED_ROTATION_MODE = "groups"
EMBED_WING_TAIL_Y180 = True
EMBED_RIG_PRESET = "changed_oldrig"


def should_flip_y180(node: dict) -> bool:
    n = (node.get("name") or "").strip().lower()
    p = (node.get("parent_var") or "").strip().lower()

    # Keep it to primary groups only so child pivots stay continuous.
    if n == "tail":
        return True
    if "wing" in n and p in {"torso", "partdefinition"}:
        return True
    return False


def parse_numbers(raw: str) -> list[float]:
    return [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", raw)]


def rad_to_deg(value: float) -> float:
    return round(math.degrees(value), 6)


def round_list(values: list[float]) -> list[float]:
    return [round(v, 6) for v in values]


def normalize_deg(v: float) -> float:
    while v > 180.0:
        v -= 360.0
    while v <= -180.0:
        v += 360.0
    return v


def normalize_rotation(rot: list[float]) -> list[float]:
    return [round(normalize_deg(float(rot[0])), 6), round(normalize_deg(float(rot[1])), 6), round(normalize_deg(float(rot[2])), 6)]


def apply_rig_origin_preset(name: str, parent_var: str, origin: list[float], rig_preset: str) -> list[float]:
    if rig_preset != "changed_oldrig" or parent_var != "partdefinition":
        return origin

    # Changed old-rig preset. Keeps top-level pivots compatible with
    # DelayLoadedModel HUMANOID fixers used at runtime.
    if name == "Torso":
        return [0.0, 0.0, 0.0]
    if name == "Head":
        return [0.0, -1.0, 0.0]
    if name in {"RightArm", "LeftArm"}:
        return [0.0, -1.0, 0.0]
    if name in {"RightLeg", "LeftLeg"}:
        return [round(origin[0], 6), round(origin[1] + 0.5, 6), round(origin[2], 6)]

    return origin


def to_blockbench_point(p: list[float], axis_preset: str) -> list[float]:
    conf = AXIS_PRESETS.get(axis_preset, AXIS_PRESETS["legacy"])
    x = -p[0] if conf["mirror_x"] else p[0]
    y = ROOT_Y - p[1] if conf["flip_y"] else p[1]
    z = -p[2] if conf["flip_z"] else p[2]
    return [x, y, z]


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


def convert_java_model(
    input_file: str,
    output_file: str,
    model_name: str = "custom_model",
    include_group_rotation: bool = False,
    axis_preset: str = "legacy",
    rotation_mode: str = "elements",
    wing_y_180: bool = False,
    rig_preset: str = "generic",
) -> tuple[int, int]:
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
    part_bb_bounds: dict[str, tuple[float, float]] = {}

    for var_name in parse_order:
        node = parts[var_name]
        world_origin = get_world_origin(var_name)
        cube_uuids = []
        min_y = float("inf")
        max_y = float("-inf")
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
            from_bb, to_bb = normalize_box(
                to_blockbench_point(from_java, axis_preset),
                to_blockbench_point(to_java, axis_preset),
            )
            from_pos = round_list(from_bb)
            to_pos = round_list(to_bb)
            min_y = min(min_y, from_pos[1], to_pos[1])
            max_y = max(max_y, from_pos[1], to_pos[1])

            w = to_pos[0] - from_pos[0]
            h = to_pos[1] - from_pos[1]
            d = to_pos[2] - from_pos[2]
            u, v = cube["uv"]
            rx, ry, rz = node["rotation"]
            # Element-space rotation mode keeps cube-local rotations.
            # Group-space mode writes rotations to outliner groups instead.
            element_rotation = normalize_rotation([-rx, ry, rz]) if rotation_mode == "elements" else [0.0, 0.0, 0.0]
            if wing_y_180 and rotation_mode == "elements" and should_flip_y180(node):
                element_rotation = normalize_rotation([element_rotation[0], element_rotation[1] + 180.0, element_rotation[2]])

            element = {
                "name": element_name,
                "box_uv": True,
                "rescale": False,
                "locked": False,
                "from": from_pos,
                "to": to_pos,
                "autouv": 0,
                "color": 0,
                "origin": round_list(to_blockbench_point(world_origin, axis_preset)),
                "faces": build_faces(u, v, w, h, d),
                "type": "cube",
                "uuid": eid,
            }
            if rotation_mode == "elements" and element_rotation != [0.0, 0.0, 0.0]:
                element["rotation"] = element_rotation
            elements.append(element)

        part_cube_uuid_map[var_name] = cube_uuids
        if min_y != float("inf"):
            part_bb_bounds[var_name] = (min_y, max_y)

    def build_outliner_node(var_name: str) -> dict:
        node = parts[var_name]
        world_origin = get_world_origin(var_name)
        adjusted_origin = round_list(to_blockbench_point(world_origin, axis_preset))
        adjusted_origin = apply_rig_origin_preset(
            node["name"],
            node["parent_var"],
            adjusted_origin,
            rig_preset,
        )

        out = {
            "name": node["name"],
            # DelayLoadedModel expects outline origins in global model space.
            # It computes local pivot by subtracting parent origin at bake time.
            "origin": adjusted_origin,
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

        if include_group_rotation:
            # Coordinate conversion:
            # - X mirrored
            # - Y axis flipped
            # DelayLoadedModel applies:
            # x = -deg, y = -deg, z = +deg
            # so we encode PartPose(rad)->deg as [-x, -y, +z] on groups.
            rx, ry, rz = node["rotation"]
            converted_rotation = normalize_rotation([-rx, -ry, rz])
            if converted_rotation != [0.0, 0.0, 0.0]:
                out["rotation"] = converted_rotation

        if wing_y_180 and should_flip_y180(node):
            rot = out.get("rotation", [0.0, 0.0, 0.0])
            if len(rot) != 3:
                rot = [0.0, 0.0, 0.0]
            rot = normalize_rotation([float(rot[0]), float(rot[1]) + 180.0, float(rot[2])])
            out["rotation"] = rot

        # Keep cube placement stable for editor-only output by default.
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
    axis_var = tk.StringVar(value="legacy")
    rotation_mode_var = tk.StringVar(value="groups")
    wing_flip_var = tk.BooleanVar(value=True)
    rig_preset_var = tk.StringVar(value="changed_oldrig")

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
        axis_preset = axis_var.get().strip() or "legacy"
        rotation_mode = rotation_mode_var.get().strip() or "groups"
        wing_y_180 = bool(wing_flip_var.get())
        rig_preset = rig_preset_var.get().strip() or "changed_oldrig"
        if rotation_mode not in ROTATION_MODES:
            rotation_mode = "groups"
        if rig_preset not in RIG_PRESETS:
            rig_preset = "changed_oldrig"

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
            parts_count, cubes_count = convert_java_model(
                input_path,
                output_path,
                model_name=model_name,
                include_group_rotation=(rotation_mode == "groups"),
                axis_preset=axis_preset,
                rotation_mode=rotation_mode,
                wing_y_180=wing_y_180,
                rig_preset=rig_preset,
            )
            status_var.set(f"Done: {output_path} (Parts: {parts_count}, Cubes: {cubes_count})")
            messagebox.showinfo(
                "Success",
                "Converted successfully.\n\n"
                f"Output: {output_path}\n"
                f"Parts: {parts_count}\n"
                f"Cubes: {cubes_count}\n"
                f"Group Rotation: {'ON' if rotation_mode == 'groups' else 'OFF'}\n"
                f"Axis Preset: {axis_preset}\n"
                f"Rotation Mode: {rotation_mode}\n"
                f"Wing/Tail Y+180: {'ON' if wing_y_180 else 'OFF'}\n"
                f"Rig Preset: {rig_preset}",
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

    tk.Label(frame, text="Axis Preset").grid(row=4, column=1, sticky="w", pady=(10, 0))
    tk.OptionMenu(frame, axis_var, "legacy", "no_mirror_x").grid(row=5, column=1, sticky="w")

    tk.Label(frame, text="Rig Preset").grid(row=6, column=0, sticky="w", pady=(10, 0))
    tk.OptionMenu(frame, rig_preset_var, "changed_oldrig", "generic").grid(row=7, column=0, sticky="w")

    tk.Label(frame, text="Rotation Mode").grid(row=6, column=1, sticky="w", pady=(10, 0))
    tk.OptionMenu(frame, rotation_mode_var, "groups", "elements").grid(row=7, column=1, sticky="w")
    tk.Checkbutton(frame, text="Wing/Tail Y +180°", variable=wing_flip_var).grid(row=8, column=1, sticky="w", pady=(8, 0))

    tk.Button(frame, text="Convert", width=16, command=do_convert).grid(row=9, column=0, sticky="w", pady=(16, 0))
    tk.Label(frame, textvariable=status_var, fg="#2b6cb0").grid(row=10, column=0, sticky="w", pady=(12, 0))

    frame.columnconfigure(0, weight=1)
    root.mainloop()


def main() -> None:
    # GUI mode:
    #   python main.py
    #   python main.py --gui
    # CLI mode:
    #   python main.py <input.java> [output.bbmodel/json] [model_name] [axis_preset] [rotation_mode] [wing_y_180] [rig_preset]
    if len(sys.argv) == 1 or (len(sys.argv) >= 2 and sys.argv[1] == "--gui"):
        launch_gui()
        return

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else str(Path(input_file).with_suffix(".bbmodel"))
    model_name = sys.argv[3] if len(sys.argv) > 3 else "custom_model"
    axis_preset = sys.argv[4] if len(sys.argv) > 4 else "legacy"
    rotation_mode = sys.argv[5] if len(sys.argv) > 5 else "groups"
    wing_y_180_arg = sys.argv[6].lower() if len(sys.argv) > 6 else "true"
    wing_y_180 = wing_y_180_arg in {"1", "true", "yes", "on"}
    rig_preset = sys.argv[7] if len(sys.argv) > 7 else "changed_oldrig"
    if rotation_mode not in ROTATION_MODES:
        rotation_mode = "groups"
    if rig_preset not in RIG_PRESETS:
        rig_preset = "changed_oldrig"

    parts_count, cubes_count = convert_java_model(
        input_file,
        output_file,
        model_name=model_name,
        include_group_rotation=(rotation_mode == "groups"),
        axis_preset=axis_preset,
        rotation_mode=rotation_mode,
        wing_y_180=wing_y_180,
        rig_preset=rig_preset,
    )
    print(f"Done: {output_file}")
    print(f"Parts: {parts_count}, Cubes: {cubes_count}")
    print(f"Group Rotation: {'ON' if rotation_mode == 'groups' else 'OFF'}")
    print(f"Axis Preset: {axis_preset}")
    print(f"Rotation Mode: {rotation_mode}")
    print(f"Wing/Tail Y+180: {'ON' if wing_y_180 else 'OFF'}")
    print(f"Rig Preset: {rig_preset}")


def launch_gui() -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox

    root = tk.Tk()
    root.title("Java Model -> Blockbench Converter")
    root.geometry("440x180")
    root.minsize(440, 180)

    status_var = tk.StringVar(value="Ready")

    def do_convert() -> None:
        input_path = filedialog.askopenfilename(
            title="Select Java model file",
            filetypes=[("Java Files", "*.java"), ("All Files", "*.*")],
        )
        if not input_path:
            return
        input_path = input_path.strip()
        if not Path(input_path).exists():
            messagebox.showerror("Input Error", f"Input file not found:\n{input_path}")
            return

        default_output = str(Path(input_path).with_suffix(".bbmodel"))
        output_path = filedialog.asksaveasfilename(
            title="Save output",
            initialfile=Path(default_output).name,
            initialdir=str(Path(default_output).parent),
            defaultextension=".bbmodel",
            filetypes=[("Blockbench Model", "*.bbmodel"), ("JSON", "*.json"), ("All Files", "*.*")],
        )
        if not output_path:
            return
        output_path = output_path.strip()

        try:
            parts_count, cubes_count = convert_java_model(
                input_path,
                output_path,
                model_name=Path(input_path).stem or "custom_model",
                include_group_rotation=(EMBED_ROTATION_MODE == "groups"),
                axis_preset=EMBED_AXIS_PRESET,
                rotation_mode=EMBED_ROTATION_MODE,
                wing_y_180=EMBED_WING_TAIL_Y180,
                rig_preset=EMBED_RIG_PRESET,
            )
            status_var.set(f"Done: {output_path} (Parts: {parts_count}, Cubes: {cubes_count})")
            messagebox.showinfo(
                "Success",
                "Converted successfully.\n\n"
                f"Output: {output_path}\n"
                f"Parts: {parts_count}\n"
                f"Cubes: {cubes_count}",
            )
        except Exception as exc:
            status_var.set("Failed")
            messagebox.showerror("Convert Failed", str(exc))

    frame = tk.Frame(root, padx=16, pady=16)
    frame.pack(fill="both", expand=True)
    tk.Button(frame, text="Convert", width=22, height=2, command=do_convert).pack(pady=(8, 10))
    tk.Label(frame, textvariable=status_var, fg="#2b6cb0", wraplength=390, justify="left").pack(anchor="w")
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

    parts_count, cubes_count = convert_java_model(
        input_file,
        output_file,
        model_name=model_name,
        include_group_rotation=(EMBED_ROTATION_MODE == "groups"),
        axis_preset=EMBED_AXIS_PRESET,
        rotation_mode=EMBED_ROTATION_MODE,
        wing_y_180=EMBED_WING_TAIL_Y180,
        rig_preset=EMBED_RIG_PRESET,
    )
    print(f"Done: {output_file}")
    print(f"Parts: {parts_count}, Cubes: {cubes_count}")
    print(f"Group Rotation: {'ON' if EMBED_ROTATION_MODE == 'groups' else 'OFF'}")
    print(f"Axis Preset: {EMBED_AXIS_PRESET}")
    print(f"Rotation Mode: {EMBED_ROTATION_MODE}")
    print(f"Wing/Tail Y+180: {'ON' if EMBED_WING_TAIL_Y180 else 'OFF'}")
    print(f"Rig Preset: {EMBED_RIG_PRESET}")


if __name__ == "__main__":
    main()
