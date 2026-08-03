from __future__ import annotations

from typing import Any

from .run_service import DurableRunService


_INSTALLED = False
_ORIGINAL_LIVING_EXPLORER_TIMELINE = DurableRunService.living_explorer_timeline


def run_queue_is_executing(service: DurableRunService, run_id: str) -> bool:
    """Return True while the developmental command queue owns the live organism.

    The Living Explorer historical timeline is a comparatively expensive forensic
    projection.  It must not be allowed to monopolize the single synchronous
    organism worker while cultivation is executing.
    """

    control = service._control(run_id)
    thread = control.thread
    return control.state in {"running", "stepping"} or bool(thread is not None and thread.is_alive())


def install_runtime_stability_patches() -> None:
    """Install conservative runtime guards used by the local Workbench launcher.

    PR #154 already guarantees request/response synchronization after a timeout.
    This guard addresses the underlying scheduling problem exposed by long runs:
    rebuilding up to 180 historical Living Explorer frames on the same worker can
    take long enough to starve the developmental queue.  During active cultivation
    the historical timeline is therefore deferred before *any* worker request is
    sent.  Once the queue is paused or idle, the normal forensic timeline remains
    available unchanged.
    """

    global _INSTALLED
    if _INSTALLED:
        return

    original = _ORIGINAL_LIVING_EXPLORER_TIMELINE

    def guarded_living_explorer_timeline(
        self: DurableRunService,
        run_id: str,
        *,
        max_frames: int = 240,
        max_nodes: int = 240,
        max_edges: int = 500,
        include_frames: bool = True,
    ) -> dict[str, Any]:
        if run_queue_is_executing(self, run_id):
            raise RuntimeError(
                "Living Explorer historical timeline is deferred while the developmental queue is running. "
                "Cultivation continues normally; pause or finish the queue before rebuilding historical frames."
            )
        return original(
            self,
            run_id,
            max_frames=max_frames,
            max_nodes=max_nodes,
            max_edges=max_edges,
            include_frames=include_frames,
        )

    guarded_living_explorer_timeline.__name__ = original.__name__
    guarded_living_explorer_timeline.__doc__ = original.__doc__
    DurableRunService.living_explorer_timeline = guarded_living_explorer_timeline
    _INSTALLED = True
