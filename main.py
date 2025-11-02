"""
Claude Agent SDK用のFastAPIアプリケーション

このアプリケーションは、Claude Agent SDKをHTTPエンドポイント経由で
非同期実行するためのWebサービスを提供します。
"""

import os
from typing import Any, Dict

from claude_agent_sdk import ClaudeAgentOptions
from fastapi import FastAPI, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware

from models import (
    CancelResponse,
    ExecuteRequest,
    ExecuteResponse,
    SessionStatus,
    StatusResponse,
)
from session_manager import SessionManager

# FastAPIアプリケーションの作成
app = FastAPI(
    title="Claude Agent SDK API",
    description="セッション管理機能付きClaude Agent SDK実行API",
    version="1.0.0",
)

# CORSミドルウェアの追加
# 注意: 本番環境では具体的なオリジンを指定してください
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では実際のオリジンを指定
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# グローバルセッションマネージャー
# アプリケーション全体でセッションの状態を管理
session_manager = SessionManager()


@app.get("/")
async def root():
    """ルートエンドポイント - APIの基本情報を返却"""
    return {
        "message": "Claude Agent SDK API",
        "version": "1.0.0",
        "endpoints": {
            "execute": "POST /execute/ - 新しいエージェントセッションを実行",
            "status": "GET /status/{session_id} - セッションの状態を取得",
            "cancel": "POST /cancel/{session_id} - 実行中のセッションをキャンセル",
        },
    }


def _build_agent_options(request: ExecuteRequest) -> ClaudeAgentOptions:
    """
    ExecuteRequestからClaudeAgentOptionsを構築する

    Args:
        request: エージェントの設定を含む実行リクエスト

    Returns:
        リクエストパラメータで設定されたClaudeAgentOptions
    """

    options_dict: Dict[str, Any] = {}

    # 作業ディレクトリ：リクエストのcwdを使用、無い場合は現在のディレクトリを使用
    options_dict["cwd"] = request.cwd or os.getcwd()

    # ツールの設定（許可）
    if request.allowed_tools is not None:
        options_dict["allowed_tools"] = _ensure_list(request.allowed_tools)

    # ツールの設定（不許可）
    if request.disallowed_tools is not None:
        options_dict["disallowed_tools"] = _ensure_list(request.disallowed_tools)

    # システムプロンプト
    if request.system_prompt is not None:
        options_dict["system_prompt"] = request.system_prompt

    # 許可モード
    if request.permission_mode is not None:
        if hasattr(request.permission_mode, "value"):
            # enumの場合は値を抽出
            options_dict["permission_mode"] = request.permission_mode.value
        else:
            # 文字列の場合
            options_dict["permission_mode"] = request.permission_mode

    # モデルの設定
    if request.model is not None:
        options_dict["model"] = request.model

    # ターン数の制限
    if request.max_turns is not None:
        options_dict["max_turns"] = request.max_turns

    # 環境変数
    if request.env is not None:
        options_dict["env"] = request.env

    return ClaudeAgentOptions(**options_dict)


def _ensure_list(value) -> list:
    """
    mypyチェック用
    値がリストであることを保証し、単一値を単一要素のリストに変換する

    Args:
        value: リストに変換する値（文字列、リスト、またはその他の反復可能なオブジェクト）

    Returns:
        値を含むリスト
    """
    if isinstance(value, str):
        return [value]
    elif isinstance(value, list):
        return value
    else:
        # 反復可能なオブジェクトをリストに変換を試みる
        try:
            return list(value)
        except TypeError:
            # 反復可能でない場合はリストでラップ
            return [value]


@app.post("/execute/", response_model=ExecuteResponse)
async def execute_agent(request: ExecuteRequest):
    """
    新しいClaudeエージェントセッションを実行
    or
    セッションIDを指定して既存のセッションを再開する

    Args:
        request: プロンプト、オプション、およびオプションのresume_session_idを含む実行リクエスト

    Returns:
        session_idとstatusを含むExecuteResponse
    """
    try:
        # リクエストからClaudeAgentOptionsを構築
        agent_options = _build_agent_options(request)

        # セッションを作成または再開
        session = await session_manager.create_session(
            request.prompt, agent_options, request.resume_session_id
        )

        # メッセージを適切に設定
        if request.resume_session_id:
            message = f"Session {session.session_id} resumed successfully"
        else:
            message = f"Session {session.session_id} started successfully"

        return ExecuteResponse(
            session_id=session.session_id,
            status=session.status,
            message=message,
        )

    except ValueError as e:
        # セッション再開エラーの場合
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create session: {str(e)}"
        )


@app.get("/status/{session_id}", response_model=StatusResponse)
async def get_status(
    session_id: str = Path(..., description="ステータス取得の対象となるセッションID"),
):
    """
    セッションの状態を取得する

    Args:
        session_id: 照会するセッションID

    Returns:
        セッションの状態とメッセージを含むStatusResponse
    """
    session = await session_manager.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return StatusResponse(
        session_id=session.session_id,
        status=session.status,
        messages=session.messages,
        result=session.result,
        error=session.error,
        duration_ms=session.get_duration_ms(),
        total_cost_usd=(
            session.result.get("total_cost_usd") if session.result and isinstance(session.result, dict) else None
        ),
    )


@app.post("/cancel/{session_id}", response_model=CancelResponse)
async def cancel_session(
    session_id: str = Path(..., description="キャンセルするセッションID"),
):
    """
    実行中のセッションをキャンセルする

    Args:
        session_id: キャンセルするセッションID

    Returns:
        更新された状態を含むCancelResponse
    """
    # セッションIDからセッションを取得
    session = await session_manager.get_session(session_id)

    if not session:
        # セッションが存在しない場合は404エラーを返す
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    if session.status != SessionStatus.RUNNING:
        raise HTTPException(
            status_code=400,
            detail=f"Session {session_id} is not running (status: {session.status})",
        )

    success = await session_manager.cancel_session(session_id)

    if not success:
        raise HTTPException(
            status_code=500, detail=f"Failed to cancel session {session_id}"
        )

    return CancelResponse(
        session_id=session_id,
        status=SessionStatus.CANCELLED,
        message=f"Session {session_id} cancelled successfully",
    )


@app.get("/sessions/")
async def list_sessions():
    """
    すべてのセッションを詳細情報付きで一覧表示する

    Returns:
        セッション詳細情報のリスト
    """
    sessions = await session_manager.get_all_sessions()
    return sessions


@app.delete("/sessions/cleanup")
async def cleanup_sessions(max_age_hours: int = 24):
    """
    古いセッションをクリーンアップする

    Args:
        max_age_hours: 保持するセッションの最大経過時間（デフォルト: 24時間）

    Returns:
        クリーンアップしたセッション数
    """
    removed = await session_manager.cleanup_old_sessions(max_age_hours)
    return {"removed": removed, "message": f"Cleaned up {removed} old sessions"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
