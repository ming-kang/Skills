#!/usr/bin/env python3
"""Rebuild the owned SVG assets from their editable svgkit layouts."""

import argparse
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2] / "visualize"
sys.dont_write_bytecode = True
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from gallery import agent, charts, flows, patterns, samples, skeletons, systems, uml
from svgkit import ValidationError


BUILDERS = {
    "gallery/agent-loop.svg": agent.agent_loop,
    "gallery/architecture.svg": systems.architecture,
    "gallery/class-diagram.svg": uml.class_diagram,
    "gallery/comparison.svg": charts.comparison,
    "gallery/data-flow.svg": systems.data_flow,
    "gallery/data-flow_mobile.svg": systems.data_flow_mobile,
    "gallery/decision-ladder.svg": flows.decision_ladder,
    "gallery/er-diagram.svg": uml.er_diagram,
    "gallery/flowchart.svg": flows.flowchart,
    "gallery/memory-architecture.svg": systems.memory_architecture,
    "gallery/mind-map.svg": flows.mind_map,
    "gallery/network-topology.svg": systems.network_topology,
    "gallery/sequence.svg": uml.sequence,
    "gallery/sequence-frames.svg": uml.sequence_frames,
    "gallery/state-machine.svg": flows.state_machine,
    "gallery/timeline-gantt.svg": charts.timeline_gantt,
    "gallery/use-case.svg": uml.use_case,
    "gallery/patterns/feedback-pipeline.svg": patterns.feedback_pipeline,
    "gallery/patterns/annotated-funnel.svg": patterns.annotated_funnel,
    "gallery/patterns/parallel-pipelines.svg": patterns.parallel_pipelines,
    "gallery/patterns/mechanism-comparison.svg": patterns.mechanism_comparison,
    "gallery/patterns/annotated-chart.svg": patterns.annotated_chart,
    "gallery/patterns/quadrant-map.svg": patterns.quadrant_map,
    "samples/hero.svg": samples.hero,
    "samples/sample-agent-loop.svg": samples.sample_agent_loop,
    "samples/sample-comparison.svg": samples.sample_comparison,
    "samples/svgkit-rag.svg": samples.svgkit_rag,
    "gallery/skeletons/architecture.svg": skeletons.architecture,
    "gallery/skeletons/comparison.svg": skeletons.comparison,
    "gallery/skeletons/data-flow.svg": skeletons.data_flow,
    "gallery/skeletons/flowchart.svg": skeletons.flowchart,
    "gallery/skeletons/sequence.svg": skeletons.sequence,
    "gallery/skeletons/state-machine.svg": skeletons.state_machine,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=SKILL_DIR / "assets")
    parser.add_argument("--filter", default="", help="Only build paths containing this text")
    parser.add_argument("--check", action="store_true", help="Check generated assets are up to date without writing")
    args = parser.parse_args()
    builders = {name: build for name, build in BUILDERS.items() if args.filter in name}
    if not builders:
        parser.error(f"no assets match {args.filter!r}")
    failures = []
    for name, build in sorted(builders.items()):
        target = args.output / name
        diagram = build()
        if args.check:
            if not target.exists() or target.read_text(encoding="utf-8") != diagram.render():
                failures.append(name)
                print(f"Out of date: {name}")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                diagram.save(str(target))
                print(f"Built {name}")
            except ValidationError:
                failures.append(name)
    if failures:
        print(f"{len(failures)} asset(s) need attention")
        return 1
    print(f"{len(builders)} assets {'are up to date' if args.check else 'built and validated'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
