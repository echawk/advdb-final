"""
Project: B561:Advanced Database Concepts - Spring 2026
Author: [Student Name]
Role: Student Starter Code

Students are expected to complete the TODO sections in this file.
Do not modify protected sections marked as [INSTRUCTOR ONLY].
"""

"""Simplified B+ tree for the student starter."""

import json
from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field

try:
    from .buffer_pool_manager import BufferPoolManager
    from .config import BPLUS_ORDER
except ImportError:
    from buffer_pool_manager import BufferPoolManager
    from config import BPLUS_ORDER


@dataclass
class BPlusTreeNode:
    page_id: int
    is_leaf: bool
    keys: list[int] = field(default_factory=list)
    values: list[int] = field(default_factory=list)
    children: list[int] = field(default_factory=list)
    next_leaf: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "page_id": self.page_id,
            "is_leaf": self.is_leaf,
            "keys": self.keys,
            "values": self.values,
            "children": self.children,
            "next_leaf": self.next_leaf,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "BPlusTreeNode":
        return cls(
            page_id=int(payload["page_id"]),
            is_leaf=bool(payload["is_leaf"]),
            keys=[int(value) for value in payload.get("keys", [])],
            values=[int(value) for value in payload.get("values", [])],
            children=[int(value) for value in payload.get("children", [])],
            next_leaf=payload.get("next_leaf"),
        )


# ================================
# [STUDENT TODO] IMPLEMENT BELOW
# ================================
class BPlusTree:
    def __init__(
        self,
        buffer_pool_manager: BufferPoolManager,
        order: int = BPLUS_ORDER,
    ) -> None:
        if order < 3:
            raise ValueError("B+ tree order must be at least 3.")

        self.buffer_pool_manager = buffer_pool_manager
        self.order = order
        root = self._allocate_node(is_leaf=True)
        self.root_page_id = root.page_id

    def _serialize(self, node: BPlusTreeNode) -> bytes:
        encoded = json.dumps(node.to_dict(), separators=(",", ":")).encode("utf-8")
        if len(encoded) > self.buffer_pool_manager.disk_manager.page_size:
            raise ValueError("Serialized B+ tree node does not fit in one page.")
        return encoded

    def _allocate_node(self, is_leaf: bool) -> BPlusTreeNode:
        page = self.buffer_pool_manager.new_page()
        node = BPlusTreeNode(page_id=page.page_id, is_leaf=is_leaf)
        self._write_node(node)
        self.buffer_pool_manager.unpin_page(node.page_id)
        return node

    def _read_node(self, page_id: int) -> BPlusTreeNode:
        page = self.buffer_pool_manager.fetch_page(page_id)
        raw = bytes(page.data).rstrip(b"\x00")
        self.buffer_pool_manager.unpin_page(page_id)
        if not raw:
            raise ValueError(f"Page {page_id} does not contain a valid B+ tree node.")
        return BPlusTreeNode.from_dict(json.loads(raw.decode("utf-8")))

    def _write_node(self, node: BPlusTreeNode) -> None:
        page = self.buffer_pool_manager.fetch_page(node.page_id)
        payload = self._serialize(node)
        page.data[:] = b"\x00" * len(page.data)
        page.data[: len(payload)] = payload
        self.buffer_pool_manager.unpin_page(node.page_id, is_dirty=True)

    def _find_leaf_page(self, key: int) -> int:
        # [STUDENT TODO] Traverse internal nodes until you reach the target leaf.
        current_page_id = self.root_page_id

        while True:
            node = self._read_node(current_page_id)
            if node.is_leaf:
                return current_page_id
            child_index = bisect_right(node.keys, key)
            current_page_id = node.children[child_index]

    def insert(self, key: int, value: int) -> None:
        # [STUDENT TODO] Insert the key/value pair into the correct leaf, split
        # overflowing nodes, and update the root if needed.
        split_result = self._insert_recursive(self.root_page_id, key, value)
        if split_result is None:
            return

        promoted_key, right_page_id = split_result
        new_root = self._allocate_node(is_leaf=False)
        new_root.keys = [promoted_key]
        new_root.children = [self.root_page_id, right_page_id]
        self._write_node(new_root)
        self.root_page_id = new_root.page_id

    def _insert_recursive(self, page_id: int, key: int, value: int) -> tuple[int, int] | None:
        # [STUDENT TODO] Use recursion to bubble split information back up the tree.
        node = self._read_node(page_id)
        if node.is_leaf:
            return self._insert_into_leaf(node, key, value)
        return self._insert_into_internal(node, key, value)

    def _insert_into_leaf(
        self,
        node: BPlusTreeNode,
        key: int,
        value: int,
    ) -> tuple[int, int] | None:
        # [STUDENT TODO] Keep keys sorted within each leaf and define the
        # duplicate-key policy.
        insert_at = bisect_left(node.keys, key)
        if insert_at < len(node.keys) and node.keys[insert_at] == key:
            node.values[insert_at] = value
            self._write_node(node)
            return None

        node.keys.insert(insert_at, key)
        node.values.insert(insert_at, value)
        if len(node.keys) <= self.order - 1:
            self._write_node(node)
            return None
        return self._split_leaf(node)

    def _insert_into_internal(
        self,
        node: BPlusTreeNode,
        key: int,
        value: int,
    ) -> tuple[int, int] | None:
        # [STUDENT TODO] Route insertion through the right child and handle a
        # child split by inserting a promoted separator key.
        child_index = bisect_right(node.keys, key)
        split_result = self._insert_recursive(node.children[child_index], key, value)
        if split_result is None:
            return None

        promoted_key, right_page_id = split_result
        node.keys.insert(child_index, promoted_key)
        node.children.insert(child_index + 1, right_page_id)
        if len(node.keys) <= self.order - 1:
            self._write_node(node)
            return None
        return self._split_internal(node)

    def _split_leaf(self, node: BPlusTreeNode) -> tuple[int, int]:
        # [STUDENT TODO] Split an overflowing leaf and maintain the leaf links.
        split_index = len(node.keys) // 2
        right_node = self._allocate_node(is_leaf=True)
        right_node.keys = node.keys[split_index:]
        right_node.values = node.values[split_index:]
        right_node.next_leaf = node.next_leaf

        node.keys = node.keys[:split_index]
        node.values = node.values[:split_index]
        node.next_leaf = right_node.page_id

        self._write_node(node)
        self._write_node(right_node)
        return right_node.keys[0], right_node.page_id

    def _split_internal(self, node: BPlusTreeNode) -> tuple[int, int]:
        # [STUDENT TODO] Split an overflowing internal node and return the
        # promoted separator key.
        split_index = len(node.keys) // 2
        promoted_key = node.keys[split_index]

        right_node = self._allocate_node(is_leaf=False)
        right_node.keys = node.keys[split_index + 1 :]
        right_node.children = node.children[split_index + 1 :]

        node.keys = node.keys[:split_index]
        node.children = node.children[: split_index + 1]

        self._write_node(node)
        self._write_node(right_node)
        return promoted_key, right_node.page_id

    def search(self, key: int) -> int | None:
        # [STUDENT TODO] Use the leaf traversal helper and scan the leaf for an
        # exact-match lookup.
        leaf_page_id = self._find_leaf_page(key)
        leaf = self._read_node(leaf_page_id)
        index = bisect_left(leaf.keys, key)
        if index < len(leaf.keys) and leaf.keys[index] == key:
            return leaf.values[index]
        return None

    def range_search(self, start_key: int, end_key: int) -> list[tuple[int, int]]:
        # [STUDENT TODO] Walk the linked leaf pages to support range queries.
        if start_key > end_key:
            return []

        results: list[tuple[int, int]] = []
        current_page_id: int | None = self._find_leaf_page(start_key)
        first_leaf = True

        while current_page_id is not None:
            leaf = self._read_node(current_page_id)
            start_index = bisect_left(leaf.keys, start_key) if first_leaf else 0

            for index in range(start_index, len(leaf.keys)):
                key = leaf.keys[index]
                if key > end_key:
                    return results
                results.append((key, leaf.values[index]))

            current_page_id = leaf.next_leaf
            first_leaf = False

        return results


__all__ = ["BPlusTreeNode", "BPlusTree"]
