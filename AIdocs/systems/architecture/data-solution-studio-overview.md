# Data Solution Studio Overview

## プロダクト概要
Data Solution Studio は、中小企業向けの社内データ活用支援AIである。  
Excel / CSV 等の社内データをアップロードすると、AI がデータ内容を理解し、
活用方法を提案し、用途に応じた実行方針を組み立て、結果と次アクションを返す。

## 今回のスコープ
今回は AI 本体の完成ではなく、以下の本番前提基盤を整備する。
- Docker Compose 構成
- Django 初期構築
- nginx / Gunicorn
- PostgreSQL / Redis
- Django-RQ worker
- Object Storage 切替可能な設定
- AIdocs の整備

## アーキテクチャ方針
- Django を中核にした modular monolith
- web / worker を分離
- app 単位で責務分割
- AI クライアントは抽象化
- ストレージは local / object storage 切替可能

## 将来の拡張想定
- datasets / profiling / semantic mapping 実装
- 活用候補生成
- 実行プラン生成
- analysis result 保存
- report 出力
