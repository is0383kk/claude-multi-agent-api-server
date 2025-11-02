# Claude Agent API Server

A production-ready FastAPI web service that enables asynchronous execution of Claude Agent SDK via HTTP API.  
Features comprehensive session management functionality for processing long-running agent tasks in the background, with real-time status monitoring and cancellation capabilities.

## ■ Available API Endpoints

| Endpoint               | Method | Description                                        |
| ---------------------- | ------ | -------------------------------------------------- |
| `/`                    | GET    | Basic API information and available endpoints list |
| `/execute/`            | POST   | Start a new Claude agent session                   |
| `/status/{session_id}` | GET    | Get session status, message history, and results   |
| `/cancel/{session_id}` | POST   | Cancel a running session                           |
| `/sessions/`           | GET    | Get detailed information of all active sessions    |
| `/sessions/cleanup`    | DELETE | Clean up old sessions                              |

## ■ File Structure

```
Claude-Agent-API-Server/
├── main.py                 # Main FastAPI application file
├── models.py               # Pydantic model definitions and validation
├── session_manager.py      # Session lifecycle management
├── client_example.py       # Production-ready Python client implementation example
├── index.html              # Interactive web test interface
└── requirements.txt        # Python dependency definitions
```

# 1. API Endpoints

## ■ Agent Execution (`POST /execute/`)

Execute agents using Claude Agent SDK.

**Request Body Example:**

```json
{
  "prompt": "Please explain Claude Agent SDK in detail",
  "system_prompt": "You are an excellent system engineer",
  "permission_mode": "acceptEdits",
  "model": "sonnet",
  "cwd": "/path/to/working/directory",
  "allowed_tools": ["Read", "Write", "Bash"]
}
```

**Response Example:**

```json
{
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "pending",
  "message": "Session 123e4567-e89b-12d3-a456-426614174000 started successfully"
}
```

## ■ Status Check (`GET /status/{session_id}`)

Get the status of a running agent.

**Response Example:**

```json
{
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "running",
  "messages": [
    {
      "type": "UserMessage",
      "content": "...",
      "timestamp": "2024-01-01T12:00:00.000Z"
    },
    {
      "type": "AssistantMessage",
      "content": "...",
      "timestamp": "2024-01-01T12:00:01.000Z"
    }
  ],
  "result": null,
  "error": null,
  "duration_ms": 1000,
  "total_cost_usd": 0.01
}
```

**Status Values:**

- `pending`: Just after session creation
- `running`: Agent is executing
- `completed`: Successfully completed
- `error`: An error occurred
- `cancelled`: Cancelled

## ■ Agent Execution Cancellation (`POST /cancel/{session_id}`)

Cancel a running agent.

**Response Example:**

```json
{
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "cancelled",
  "message": "Session 123e4567-e89b-12d3-a456-426614174000 cancelled successfully"
}
```

## ■ Session List Retrieval (`GET /sessions/`)

Get detailed information of all active sessions.

**Response Example:**

```json
[
  {
    "session_id": "123e4567-e89b-12d3-a456-426614174000",
    "status": "running",
    "prompt": "Create a Hello World program in Python",
    "created_at": "2024-01-01T12:00:00.000Z",
    "start_time": "2024-01-01T12:00:01.000Z",
    "end_time": null,
    "error": null,
    "result": null,
    "message_count": 5
  }
]
```

## ■ Old Session Cleanup (`DELETE /sessions/cleanup`)

Delete sessions older than the specified time.

**Query Parameters:**

- `max_age_hours`: Maximum retention time (default: 24 hours)

**Response Example:**

```json
{
  "removed": 5,
  "message": "Cleaned up 5 old sessions"
}
```

# 2. Setup and Execution

## ■ Prerequisites

- Python 3.8 or higher
- Claude Code CLI (`npm install -g @anthropic-ai/claude-code`)

## ■ Library Installation

```bash
pip install -r requirements.txt
```

## ■ Server Startup

```bash
python main.py
```

or

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

# 3. Quick Start

## ■ Pattern 1: Test with Web Interface

After starting the server, open `index.html` in a browser for GUI operation.

## ■ Pattern 2: Test with Python Client

Running `client_example.py` executes batch processing for all API endpoints.

```python
python client_example.py
```

# 4. Important Notes and Best Practices

## ■ Memory Management

- Sessions are stored in memory and are not automatically deleted
- Regularly clean up with `/sessions/cleanup` or restart the server

## ■ Performance

- Long-running agents continue to consume server resources
- Be mindful of the number of concurrent sessions
- Actively cancel unnecessary sessions

## ■ Security

- Configure CORS settings appropriately for production environments

## ■ License

MIT License

---

# Claude Agent API Server

Claude Agent SDK を HTTP API 経由で非同期実行できるようにした本格的な FastAPI Web サービスです。  
セッション管理機能を備え、長時間実行されるエージェントタスクをバックグラウンドで処理し、リアルタイムでの状態監視とキャンセル機能を提供します。

## ■ 提供している API エンドポイント一覧

| エンドポイント         | メソッド | 説明                                         |
| ---------------------- | -------- | -------------------------------------------- |
| `/`                    | GET      | API の基本情報と利用可能エンドポイント一覧   |
| `/execute/`            | POST     | 新しい Claude エージェントセッションを開始   |
| `/status/{session_id}` | GET      | セッションの状態、メッセージ履歴、結果を取得 |
| `/cancel/{session_id}` | POST     | 実行中のセッションをキャンセル               |
| `/sessions/`           | GET      | すべてのアクティブセッションの詳細情報を取得 |
| `/sessions/cleanup`    | DELETE   | 古いセッションをクリーンアップ               |

## ■ ファイル構成

```
Claude-Agent-API-Server/
├── main.py                 # FastAPIアプリケーションのメインファイル
├── models.py               # Pydanticモデル定義とバリデーション
├── session_manager.py      # セッションライフサイクル管理
├── client_example.py       # 本格的なPythonクライアント実装例
├── index.html              # インタラクティブWebテストインターフェース
└── requirements.txt        # Python依存パッケージ定義
```

# 1. API エンドポイントについて

## ■ エージェント実行 (`POST /execute/`)

Claude Agent SDK によるエージェントを実行します。

**リクエストボディ例:**

```json
{
  "prompt": "Claude Agent SDKについて詳しく解説してください",
  "system_prompt": "あなたは優秀なシステムエンジニアです",
  "permission_mode": "acceptEdits",
  "model": "sonnet",
  "cwd": "/path/to/working/directory",
  "allowed_tools": ["Read", "Write", "Bash"]
}
```

**レスポンス例:**

```json
{
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "pending",
  "message": "Session 123e4567-e89b-12d3-a456-426614174000 started successfully"
}
```

## ■ ステータス確認 (`GET /status/{session_id}`)

実行中のエージェントのステータスを取得します。

**レスポンス例:**

```json
{
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "running",
  "messages": [
    {
      "type": "UserMessage",
      "content": "...",
      "timestamp": "2024-01-01T12:00:00.000Z"
    },
    {
      "type": "AssistantMessage",
      "content": "...",
      "timestamp": "2024-01-01T12:00:01.000Z"
    }
  ],
  "result": null,
  "error": null,
  "duration_ms": 1000,
  "total_cost_usd": 0.01
}
```

**ステータス値:**

- `pending`: セッション作成直後
- `running`: エージェント実行中
- `completed`: 正常に完了
- `error`: エラーが発生
- `cancelled`: キャンセルされた

## ■ エージェント実行中断 (`POST /cancel/{session_id}`)

実行中のエージェントを中断します。

**レスポンス例:**

```json
{
  "session_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "cancelled",
  "message": "Session 123e4567-e89b-12d3-a456-426614174000 cancelled successfully"
}
```

## ■ セッション一覧取得 (`GET /sessions/`)

すべてのアクティブセッションの詳細情報を取得します。

**レスポンス例:**

```json
[
  {
    "session_id": "123e4567-e89b-12d3-a456-426614174000",
    "status": "running",
    "prompt": "PythonでHello Worldプログラムを作成してください",
    "created_at": "2024-01-01T12:00:00.000Z",
    "start_time": "2024-01-01T12:00:01.000Z",
    "end_time": null,
    "error": null,
    "result": null,
    "message_count": 5
  }
]
```

## ■ 古いセッションのクリーンアップ (`DELETE /sessions/cleanup`)

指定した時間より古いセッションを削除します。

**クエリパラメータ:**

- `max_age_hours`: 保持する最大時間（デフォルト: 24 時間）

**レスポンス例:**

```json
{
  "removed": 5,
  "message": "Cleaned up 5 old sessions"
}
```

# 2. 実行方法

## ■ 前提条件

- Python 3.8 以上
- Claude Code CLI (`npm install -g @anthropic-ai/claude-code`)

## ■ ライブラリのインストール

```bash
pip install -r requirements.txt
```

## ■ サーバーの起動

```bash
python main.py
```

または

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

# 3. クイックスタート

## ■ パターン１：Web インターフェースでテスト

サーバーを起動した後、`index.html`をブラウザで開いて GUI で操作できます。

## ■ パターン２：Python クライアントでテスト

`client_example.py`を実行すると、API エンドポイントで定義されている処理を一括実行できます。

```python
python client_example.py
```

# 4. 注意事項とベストプラクティス

## ■ メモリ管理

- セッションはメモリ内に保存され、自動削除されません
- 定期的に `/sessions/cleanup` でクリーンアップかサーバの再起動をしてください

## ■ パフォーマンス

- 長時間実行エージェントはサーバーリソースを消費し続けます
- 同時実行セッション数に注意してください
- 不要なセッションは積極的にキャンセルしてください

## ■ セキュリティ

- 本番環境では CORS 設定を適切に配置してください

## ■ ライセンス

MIT License
