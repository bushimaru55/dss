# 2026-03-27 Preprocessing Foundation

## 目的
Excel/CSV 前処理の精度と可観測性を向上し、profiling/semantic mapping の誤読率を低減する。

## 追加対象
- datasets（preview・processing 状態拡張）
- profiling（前処理 + 列プロファイル強化）
- semantic_mapping（候補生成・修正保持）

## 追加内容
- pandas/openpyxl/pandera を使った前処理基盤
- preview API とシート情報 API
- header 候補判定 / warning 生成
- semantic 候補生成 API
- DatasetFile 分離（1:1）
- profiling / semantic_mapping の履歴モデル分離
- analysis_runs（chat/ask 非同期分析）追加
- rag（index/search）最小実装を追加
- runbook / verification 追記

## 備考
- DuckDB は将来 reader 差し替え先として導入余地を残す（今回未採用）。
