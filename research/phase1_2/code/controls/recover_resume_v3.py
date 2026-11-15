#!/usr/bin/env python3
"""RadiantDAQ: recover existing 10,000-primary OFF run with ROOT cycle handling.

DOES NOT edit/re-run the previous OFF raw simulation or other Phase 1.2 runs.
Writes a NEW workspace; imports known original script read-only to keep physics,
seed plan, statistics, and output validation identical. Uses the latest ROOT PhaseSpace TTree cycle, checking earlier cycles for
matching event identities and energies rather than double-counting snapshots.

Stops without interpreting results if the second tree is another distinct
phase-space event stream or if anything fails the ROOT/Dose or physics checks.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import importlib.util
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ORIGINAL_SHA = "69471a3524f66eb6723fe90af6010e745a3d508562c9e34a6b496dc5ae5426bb"
SOURCE_MACRO_SHA = "ad908f97c4710f00f0a5506c6e9217768a923f781d1a572e1adcf58ffc6651e5"
RUN_NAME = "BGO_T20_OFF_rep1_seed8457101"
ROOT_FIELDS = {"EventID", "Ekine", "ParticleName"}


def load_original(script: Path):
    if not script.is_file() or sha256(script) != ORIGINAL_SHA:
        raise ValueError("Original paired script missing or differs from reviewed version; no modifications made")
    spec = importlib.util.spec_from_file_location("radiantdaq_original_paired_control", script)
    if spec is None or spec.loader is None:
        raise ValueError("Cannot import original paired script")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if mod.SOURCE_SHA256 != SOURCE_MACRO_SHA or tuple(mod.BASE_SEEDS) != (8457101, 8457202):
        raise ValueError("Original study source or seeds mismatch")
    return mod


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def identify_phase_space(root, path: Path):
    """Select newest ROOT TTree *cycle* and cross-check older snapshots.

    ROOT names such as PhaseSpace;1 and PhaseSpace;2 are snapshots/cycles of
    ONE named tree, not independent event streams. Never sum their entries.
    Another uniquely named tree with event fields is still an error.
    """
    import numpy as np

    trees = []
    for key, obj in root.items(recursive=False, cycle=True):
        if not (hasattr(obj, "num_entries") and hasattr(obj, "keys")):
            continue
        if ";" not in key or not key.rsplit(";", 1)[1].isdigit():
            raise ValueError(f"{path.name}: malformed ROOT tree key {key!r}")
        label, cycle_text = key.rsplit(";", 1)
        trees.append({
            "key": key, "label": label, "cycle": int(cycle_text),
            "tree": obj, "branches": set(obj.keys()),
            "rows": int(obj.num_entries),
        })
    print(f"  ROOT {path.name} cycles: " + ", ".join(
        f"{t['key']} ({t['rows']} rows, {len(t['branches'])} branches)"
        for t in trees), flush=True)

    phase = [t for t in trees if t["label"] == "PhaseSpace"]
    if not phase:
        raise ValueError(f"{path.name}: no PhaseSpace TTree found")
    if len({t["cycle"] for t in phase}) != len(phase):
        raise ValueError(f"{path.name}: repeated PhaseSpace cycle identifier")
    if any(not ROOT_FIELDS <= t["branches"] for t in phase):
        raise ValueError(f"{path.name}: PhaseSpace cycle missing required event fields")
    unrelated = [t["key"] for t in trees
                 if t["label"] != "PhaseSpace" and ROOT_FIELDS <= t["branches"]]
    if unrelated:
        raise ValueError(f"{path.name}: different event-bearing tree(s) exist: {unrelated}")

    latest = max(phase, key=lambda t: t["cycle"])
    latest_tree = latest["tree"]
    # Compare stored snapshots. Do not assume equal row counts/branch lists
    # alone establish equal event content. The older cycles are NOT accumulated.
    compare_branches = [name for name in ("EventID", "Ekine", "TrackID", "ParentID")
                        if all(name in t["branches"] for t in phase)]
    snapshots_equal = True
    if len(phase) > 1:
        for t in phase:
            if t is latest:
                continue
            if t["rows"] != latest["rows"]:
                raise ValueError(
                    f"{path.name}: older cycle {t['key']} contains {t['rows']} rows vs "
                    f"latest {latest['key']} {latest['rows']}; manual check required")
            for name in compare_branches:
                first = latest_tree[name].array(library="np")
                second = t["tree"][name].array(library="np")
                if not np.array_equal(first, second, equal_nan=False):
                    snapshots_equal = False
                    raise ValueError(
                        f"{path.name}: {name} differs between {t['key']} and "
                        f"{latest['key']}; cannot confirm duplicate cycles")
        print(f"  Selected latest ROOT cycle {latest['key']}; "
              f"{len(phase)-1} earlier cycle(s) match on {compare_branches}; "
              "no double counting.", flush=True)
    else:
        print(f"  Selected unique ROOT cycle {latest['key']}.", flush=True)

    inventory = [{
        "key": t["key"], "rows": t["rows"],
        "branches": sorted(t["branches"]),
        "selected": t is latest,
        "root_cycle_not_independent_tree": t["label"] == "PhaseSpace",
        "crosschecked_numeric_branches": compare_branches if t["label"] == "PhaseSpace" else [],
    } for t in trees]
    return latest_tree, inventory


def audit_fixed(mod, folder: Path, n: int, derived: Path) -> dict:
    import numpy as np
    import uproot
    root=folder/"hits.root"
    if not root.is_file():
        raise ValueError(f"Missing {root}")
    with uproot.open(root) as r:
        t=r["Hits"]
        event_ids=t["eventID"].array(library="np")
        energy_mev=t["edep"].array(library="np")
    if (not len(event_ids) or not np.issubdtype(event_ids.dtype,np.integer)
            or event_ids.min()<0 or event_ids.max()>=n or len(event_ids)!=len(energy_mev)
            or not np.isfinite(energy_mev).all() or np.any(energy_mev < -1e-8)):
        raise ValueError("Invalid ROOT Hits eventIDs or deposited energies")
    per_keV=np.bincount(event_ids,weights=energy_mev,minlength=n)*1000.0
    if not np.isfinite(per_keV).all() or np.any(per_keV < -1e-6) or np.any(per_keV > 511.1):
        raise ValueError("Out-of-range deposited energy")
    root_total=float(per_keV.sum(dtype=np.float64)/1000.0)
    dose_total,dose_hashes=mod.read_dose_total(folder)
    if abs(root_total-dose_total)>max(0.0005,1e-6*abs(root_total)):
        raise ValueError(f"ROOT/DoseActor mismatch: {root_total} vs {dose_total} MeV")
    phsp={}
    for name in ("outgoing.root","created.root"):
        path=folder/name
        if not path.is_file():
            raise ValueError(f"Missing {path}")
        with uproot.open(path) as file:
            tree, inventory=identify_phase_space(file,path)
            ids=tree["EventID"].array(library="np")
            en=tree["Ekine"].array(library="np")
            if (len(ids)!=tree.num_entries or len(en)!=tree.num_entries
                    or not np.issubdtype(ids.dtype,np.integer)
                    or (len(ids)>0 and (ids.min()<0 or ids.max()>=n))
                    or not np.isfinite(en).all() or np.any(en<0)):
                raise ValueError(f"{name}: invalid event IDs or kinetic energy")
            phsp[name]={"rows":int(tree.num_entries), "sha256":sha256(path), "trees":inventory}
    if derived.exists():
        raise FileExistsError(f"No overwrite of derived CSV: {derived}")
    derived.parent.mkdir(parents=True, exist_ok=True)
    with derived.open("w",newline="") as f:
        writer=csv.writer(f)
        writer.writerow(("eventID","deposited_energy_keV"))
        writer.writerows((i,f"{v:.12f}") for i,v in enumerate(per_keV))
    return {
        "histories":n,
        "hit_rows":int(len(event_ids)),
        "interacting_events":int(np.count_nonzero(per_keV>1e-6)),
        "roi_400_440":int(np.count_nonzero((per_keV>=400)&(per_keV<=440))),
        "nearfull_490_520":int(np.count_nonzero((per_keV>=490)&(per_keV<=520))),
        "total_root_edep_MeV":root_total,
        "total_dose_edep_MeV":dose_total,
        "root_dose_abs_diff_MeV":abs(root_total-dose_total),
        "hits_root_sha256":sha256(root),
        "energy_csv_sha256":sha256(derived),
        "energy_csv_path":str(derived),
        "dose_hashes":dose_hashes,
        "phase_space":phsp,
    }


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-script",type=Path,
        default=Path("/mnt/c/Users/burha/Downloads/RadiantDAQ_Region_Fluo_Paired_2026.py"))
    parser.add_argument("--previous",type=Path,
        default=Path.home()/"radiantdaq_region_fluo_paired_2026")
    parser.add_argument("--output",type=Path,
        default=Path.home()/"radiantdaq_region_fluo_paired_recovered_v3_2026")
    parser.add_argument("--workspace",type=Path,
        default=Path.home()/"radiantdaq_phase1_2_full_2026")
    parser.add_argument("--gate",type=Path,default=Path.home()/"gate_build/Gate")
    parser.add_argument("--timeout",type=int,default=7200)
    parser.add_argument("--audit-only",action="store_true",
        help="Validate existing OFF ROOT/Dose without GATE; writes only NEW derived workspace")
    parser.add_argument("--inspect-only",action="store_true",
        help="READ-ONLY: inspect outgoing/created ROOT tree names, no directories or GATE runs")
    a=parser.parse_args()
    mod=load_original(a.original_script.expanduser().resolve())
    old=a.previous.expanduser().resolve()
    output=a.output.expanduser().resolve()
    work=a.workspace.expanduser().resolve()
    gate=a.gate.expanduser().resolve()
    if not 60<=a.timeout<=86400:
        parser.error("--timeout must be 60..86400")
    if output.exists():
        raise SystemExit(f"New output directory already exists; refusing overwrite: {output}")
    if work in output.parents or old in output.parents or output in (old,work):
        raise SystemExit("Output cannot be inside old workspace or original campaign")
    source=work/"runs"/mod.SOURCE_ID/"run.mac"
    validated=work/"runs"/mod.SOURCE_ID/"validated.json"
    if not source.is_file() or not validated.is_file() or not gate.is_file():
        raise ValueError("Missing source macro, source validation, or GATE executable")
    if sha256(source)!=SOURCE_MACRO_SHA or json.loads(validated.read_text()).get("macro_sha256")!=SOURCE_MACRO_SHA:
        raise ValueError("Source macro SHA-256 mismatch; refusing")
    manifest_file=old/"manifest.json"
    if not manifest_file.is_file():
        raise ValueError(f"Original control manifest missing: {manifest_file}")
    original=json.loads(manifest_file.read_text())
    rows=original.get("runs",[])
    if (len(rows)!=1 or rows[0].get("condition")!="OFF"
            or rows[0].get("seed")!=8457101 or rows[0].get("gate_exit_code")!=0
            or rows[0].get("status")!="INVALID"
            or rows[0].get("validation_error")!="ValueError: outgoing.root should have 1 phase-space tree; got 2"
            or original.get("events_per_run")!=10000
            or original.get("source_macro_sha256")!=SOURCE_MACRO_SHA):
        raise ValueError("Previous run manifest does not match expected recoverable state; refuse to infer")
    old_row=rows[0]
    old_dir=(old/"runs"/RUN_NAME).resolve()
    if Path(old_row.get("path","")).resolve()!=old_dir:
        raise ValueError("Prior run path doesn't match expected folder")
    old_macro=old_dir/"run.mac"
    old_log=old_dir/"gate.log"
    if not old_macro.is_file() or not old_log.is_file():
        raise ValueError("Missing completed OFF run inputs")
    if sha256(old_macro)!=old_row.get("macro_sha256") or sha256(old_log)!=old_row.get("log_sha256"):
        raise ValueError("Completed OFF run macro/log hash changed")
    log=old_log.read_text(errors="replace")
    flags=mod.parse_transport_flags(log)
    bad=[x for x in ("*** Fatal Exception ***", "G4Exception : de0001", "Command not found",
                     "Illegal application state", "*** Run must be aborted ***") if x in log]
    if (len(flags)<2 or any(tuple(f)!=(0,1,1) for f in flags) or bad
           or mod.CONTROL_END not in log or "Acquisition starts!" not in log):
        raise ValueError("Completed OFF run log/flags not valid")
    if a.inspect_only:
        import uproot
        for name in ("outgoing.root", "created.root"):
            path=old_dir/name
            with uproot.open(path) as file:
                tree, inventory=identify_phase_space(file,path)
                print(json.dumps({"file":str(path),"selected_phase_space_rows":int(tree.num_entries),
                                  "inventory":inventory},indent=2),flush=True)
        print("INSPECTION PASSED: No files created or changed.",flush=True)
        return 0
    # Everything above is read-only. New output starts here.
    output.mkdir(parents=True,exist_ok=False)
    (output/"runs").mkdir()
    (output/"derived").mkdir()
    manifest={
        "project":"RadiantDAQ fluorescence region paired study 2026 -- recovery v3",
        "created_at_utc":datetime.now(timezone.utc).isoformat(),
        "status":"STARTED", "source_macro":str(source),
        "source_macro_sha256":SOURCE_MACRO_SHA, "gate_executable":str(gate),
        "events_per_run":10000,"expected_runs":4,"expected_total_histories":40000,
        "independent_seed_count":2,"seeds":[8457101,8457202],
        "method":"Post-initialization region fluorescence: global and world ON; crystal OFF or ON; Auger/PIXE ON",
        "original_workspace_readonly":str(old),
        "runs":[],
    }
    def save():
        (output/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
        mod.write_summary(output,manifest)
    try:
        print("[RECOVERY 1/4] Auditing existing 10,000-event OFF run READ-ONLY",flush=True)
        result={k:v for k,v in old_row.items() if k not in ("validation_error",)}
        derived=output/"derived"/"reused_OFF_seed8457101_energy_per_primary_keV.csv"
        result.update(audit_fixed(mod,old_dir,10000,derived))
        result.update({"status":"VALIDATED", "reused_existing_raw":True,
                       "recovery":"Original GATE data never changed or rerun"})
        manifest["runs"].append(result)
        print(json.dumps({"status":result["status"],"roi_400_440":result["roi_400_440"],
                          "nearfull_490_520":result["nearfull_490_520"],
                          "root_dose_abs_diff_MeV":result["root_dose_abs_diff_MeV"]},indent=2),flush=True)
        save()
        if a.audit_only:
            manifest["status"]="AUDIT_ONLY_ONE_RUN_VALIDATED"
            save()
            print("AUDIT-ONLY COMPLETE. New output:",output,flush=True)
            return 0
        mod.audit_outputs=lambda folder,n: audit_fixed(mod,folder,n,
            folder/"deposited_energy_per_primary_keV.csv")
        raw=source.read_text()
        sequence=[(1,8457101,"ON"),(2,8457202,"OFF"),(2,8457202,"ON")]
        for i,seed,fluo in sequence:
            directory=output/"runs"/f"BGO_T20_{fluo}_rep{i}_seed{seed}"
            directory.mkdir(exist_ok=False)
            (directory/"run.mac").write_text(mod.build_macro(raw,fluo=fluo,seed=seed,events=10000))
            print(f"[GATE {len(manifest['runs'])+1}/4] {fluo} seed={seed} primaries=10000",flush=True)
            res=mod.run_case(gate,directory,fluo,10000,a.timeout)
            res.update({"seed":seed,"replicate":i,"path":str(directory),"reused_existing_raw":False})
            manifest["runs"].append(res)
            print(json.dumps({k:res.get(k) for k in ("condition","status","gate_exit_code",
                  "crystal_flags_at_transport","roi_400_440","nearfull_490_520",
                  "root_dose_abs_diff_MeV","validation_error") if k in res},indent=2),flush=True)
            save()
            if res["status"]!="VALIDATED":
                manifest["status"]="STOPPED_INVALID_RUN"
                save()
                print("STOP: remaining runs not started; original raw remains unchanged",flush=True)
                return 2
        manifest["status"]="VALIDATED"
        save()
        print("ALL FOUR VALIDATED; see",output/"SUMMARY.json",flush=True)
        return 0
    except Exception as exc:
        manifest["status"]="RECOVERY_ERROR"
        manifest["recovery_error"]=f"{type(exc).__name__}: {exc}"
        save()
        raise

if __name__=="__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"STOP: {type(exc).__name__}: {exc}",file=sys.stderr)
        sys.exit(2)
