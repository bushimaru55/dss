# 変更記録: SPEC-TI-014 §20（MVP 後続の未着手境界）

**日付**: 2026-04-08  
**関連**: [SPEC-TI-014 §20](../specs/table-intelligence/04_system/SPEC-TI-014-api.md#20-未着手境界と次実装前提)、[INDEX-table-intelligence](../00_管理/INDEX-table-intelligence.md)

## 概要

read-only 参照面の文書整合（OpenAPI / example / spot check）完了後、**次の backend 実装に入る直前**として、**未着手の論点**と **次実装候補（未確定）**、**今回の範囲外**を **SPEC-TI-014 に集約**した。新しい実行挙動・gating／readiness の詳細仕様は **定義していない**。

## 主な内容（§20）

- **固定済み境界**: 005 正本、011 補助（005 を上書きしない）、013 read-only 参照、canonical 系は観測派生、`semantic_lock_in` は MVP で false。
- **未着手**: gating 本格化、caution／readiness 詳細、unresolved と昇格の詳細、候補 API への参照面展開、011→013 補助拡張、厳密 Schema 化、`semantic_lock_in` 導入。
- **次候補の例**: 上記を **列挙のみ**（優先・確定仕様ではない）。
- **位置づけ**: 実装前の境界整理。大改稿ではない。

## コード・OpenAPI

- **変更なし**（AIdocs のみ）。
