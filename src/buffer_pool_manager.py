"""
Project: B561:Advanced Database Concepts - Spring 2026
Author: [Student Name]
Role: Student Starter Code

Students are expected to complete the TODO sections in this file.
Do not modify protected sections marked as [INSTRUCTOR ONLY].
"""

"""Buffer pool manager for the student starter."""

try:
    from .config import BUFFER_POOL_SIZE
    from .disk_manager import DiskManager
    from .models import Page
    from .replacement import ClockReplacementPolicy, LRUReplacementPolicy
except ImportError:
    from config import BUFFER_POOL_SIZE
    from disk_manager import DiskManager
    from models import Page
    from replacement import ClockReplacementPolicy, LRUReplacementPolicy


# ================================
# [STUDENT TODO] IMPLEMENT BELOW
# ================================
class BufferPoolManager:
    def __init__(
        self,
        pool_size: int = BUFFER_POOL_SIZE,
        disk_manager: DiskManager | None = None,
        replacement_policy: str = "lru",
    ) -> None:
        if pool_size <= 0:
            raise ValueError("Buffer pool size must be positive.")

        self.pool_size = pool_size
        self.disk_manager = disk_manager if disk_manager is not None else DiskManager()
        self.page_table: dict[int, int] = {}
        self.frames: list[Page | None] = [None for _ in range(pool_size)]
        self.free_list = list(range(pool_size))
        self.replacer = self._build_replacer(replacement_policy)
        self.replacement_policy_name = replacement_policy.lower()

        self.hit_count = 0
        self.miss_count = 0
        self.eviction_count = 0
        self.flush_count = 0
        self.delete_count = 0

        # ================================
        # [INSTRUCTOR ONLY] DO NOT MODIFY
        # ================================
        # [INSTRUCTOR ONLY] Shared-state orchestration or locking belongs here.

    def _build_replacer(self, replacement_policy: str):
        normalized = replacement_policy.lower()
        if normalized == "lru":
            return LRUReplacementPolicy(self.pool_size)
        if normalized == "clock":
            return ClockReplacementPolicy(self.pool_size)
        raise ValueError(f"Unknown replacement policy: {replacement_policy}")

    def _get_frame_id(self, page_id: int) -> int | None:
        return self.page_table.get(page_id)

    def _mark_frame_evictable(self, frame_id: int, evictable: bool) -> None:
        # [STUDENT TODO] Coordinate pin/unpin state with the replacement policy.
        self.replacer.record_access(frame_id)
        self.replacer.set_evictable(frame_id, evictable)

    def _evict_if_needed(self) -> int:
        if self.free_list:
            return self.free_list.pop(0)

        # [STUDENT TODO] Evict a victim frame, flush it if dirty, and recycle
        # the frame id for the next page.
        frame_id = self.replacer.evict()
        if frame_id is None:
            raise RuntimeError("No frame is available for eviction.")

        victim = self.frames[frame_id]
        if victim is None:
            return frame_id

        if victim.is_dirty:
            self.disk_manager.write_page(victim)
            self.flush_count += 1

        self.page_table.pop(victim.page_id, None)
        self.frames[frame_id] = None
        self.eviction_count += 1
        return frame_id

    def fetch_page(self, page_id: int) -> Page:
        # [STUDENT TODO] Implement hit detection, miss handling, pinning, and
        # stats updates here.
        frame_id = self._get_frame_id(page_id)
        if frame_id is not None:
            page = self.frames[frame_id]
            if page is None:
                raise ValueError(f"Frame {frame_id} does not contain page {page_id}.")
            self.hit_count += 1
            page.pin_count += 1
            self._mark_frame_evictable(frame_id, evictable=False)
            return page

        self.miss_count += 1
        self.disk_manager._validate_page_id(page_id)
        frame_id = self._evict_if_needed()
        page = self.disk_manager.read_page(page_id)
        page.pin_count = 1
        self.frames[frame_id] = page
        self.page_table[page_id] = frame_id
        self._mark_frame_evictable(frame_id, evictable=False)
        return page

    def new_page(self) -> Page:
        # [STUDENT TODO] Allocate a new disk page and place it in a buffer
        # frame.
        frame_id = self._evict_if_needed()
        page_id = self.disk_manager.allocate_page()
        page = Page(page_id=page_id)
        page.pin_count = 1
        self.frames[frame_id] = page
        self.page_table[page_id] = frame_id
        self._mark_frame_evictable(frame_id, evictable=False)
        return page

    def unpin_page(self, page_id: int, is_dirty: bool = False) -> bool:
        # [STUDENT TODO] Decrement the pin count, mark the page dirty if
        # needed, and make it evictable once no clients still hold it.
        frame_id = self._get_frame_id(page_id)
        if frame_id is None:
            return False

        page = self.frames[frame_id]
        if page is None or page.pin_count <= 0:
            return False

        page.pin_count -= 1
        if is_dirty:
            page.is_dirty = True
        if page.pin_count == 0:
            self._mark_frame_evictable(frame_id, evictable=True)
        return True

    def flush_page(self, page_id: int) -> bool:
        # [STUDENT TODO] Write a single page back to disk and clear its dirty
        # flag.
        frame_id = self._get_frame_id(page_id)
        if frame_id is None:
            return False

        page = self.frames[frame_id]
        if page is None:
            return False

        if page.is_dirty:
            self.disk_manager.write_page(page)
            self.flush_count += 1
        return True

    def flush_all_pages(self) -> None:
        # [STUDENT TODO] Flush every dirty page currently cached in memory.
        for page_id, frame_id in list(self.page_table.items()):
            page = self.frames[frame_id]
            if page is not None and page.is_dirty:
                self.flush_page(page_id)

    def delete_page(self, page_id: int) -> bool:
        # [STUDENT TODO] Remove an unpinned page from the buffer and then clear
        # its disk slot.
        frame_id = self._get_frame_id(page_id)
        if frame_id is not None:
            page = self.frames[frame_id]
            if page is None:
                return False
            if page.pin_count > 0:
                return False

            self.page_table.pop(page_id, None)
            self.frames[frame_id] = None
            self.replacer.remove(frame_id)
            self.free_list.append(frame_id)

        try:
            deleted = self.disk_manager.delete_page(page_id)
        except IndexError:
            return False

        if deleted:
            self.delete_count += 1
        return deleted

    def get_stats(self) -> dict[str, float]:
        disk_stats = self.disk_manager.get_stats()
        return {
            "pool_size": self.pool_size,
            "policy": self.replacement_policy_name,
            "hits": self.hit_count,
            "misses": self.miss_count,
            "evictions": self.eviction_count,
            "flushes": self.flush_count,
            "deletes": self.delete_count,
            "disk_reads": disk_stats["reads"],
            "disk_writes": disk_stats["writes"],
            "simulated_time_ms": disk_stats["simulated_time_ms"],
        }
