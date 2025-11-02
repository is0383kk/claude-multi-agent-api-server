"""
Claude Agent SDK API用のFastAPIリクエスト/レスポンスモデル

このモジュールは、APIのリクエストとレスポンスのデータ構造を定義します。
Pydanticを使用してデータ検証とシリアライゼーションを提供します。
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    """セッションの状態を表す列挙型

    - PENDING: セッションが作成されたが、まだ実行されていない
    - RUNNING: エージェントが実行中
    - COMPLETED: 実行が正常に完了
    - ERROR: 実行中にエラーが発生
    - CANCELLED: ユーザーによってキャンセルされた
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class PermissionMode(str, Enum):
    """エージェントの許可モードを表す列挙型

    - DEFAULT: デフォルトの許可モード
    - ACCEPT_EDITS: 編集操作を自動承認
    - PLAN: プランモード（実際の変更は行わない）
    - BYPASS_PERMISSIONS: 許可チェックをバイパス
    """

    DEFAULT = "default"
    ACCEPT_EDITS = "acceptEdits"
    PLAN = "plan"
    BYPASS_PERMISSIONS = "bypassPermissions"


class ExecuteRequest(BaseModel):
    """/execute/エンドポイント用のリクエストモデル

    Claudeエージェントの実行に必要なすべてのパラメータを定義します。
    resume_session_idが指定された場合は既存セッションを再開し、
    指定されない場合は新規セッションを作成します。
    """

    prompt: str = Field(..., description="エージェントに送信するプロンプト")
    allowed_tools: Optional[List[str]] = Field(
        None, description="使用を許可するツール名のリスト"
    )
    system_prompt: Optional[str] = Field(None, description="システムプロンプト")
    permission_mode: Optional[PermissionMode] = Field(None, description="許可モード")
    model: Optional[str] = Field(
        None, description="使用するモデル (sonnet, opus, haiku)"
    )
    cwd: Optional[str] = Field(None, description="現在の作業ディレクトリ")
    max_turns: Optional[int] = Field(None, description="最大会話ターン数")
    env: Optional[Dict[str, str]] = Field(None, description="環境変数")
    disallowed_tools: Optional[List[str]] = Field(
        None, description="使用を禁止するツール名のリスト"
    )
    resume_session_id: Optional[str] = Field(
        None, description="再開するセッションID。指定された場合、同一セッションIDで既存セッションを再開"
    )


class ExecuteResponse(BaseModel):
    """/execute/エンドポイント用のレスポンスモデル

    エージェント実行リクエストの結果を返します。
    """

    session_id: str = Field(..., description="生成されたセッションID")
    status: SessionStatus = Field(..., description="初期状態")
    message: str = Field(..., description="状態メッセージ")


class CancelResponse(BaseModel):
    """/cancel/{session_id}エンドポイント用のレスポンスモデル

    セッションキャンセル操作の結果を返します。
    """

    session_id: str = Field(..., description="キャンセルされたセッションID")
    status: SessionStatus = Field(..., description="更新された状態")
    message: str = Field(..., description="状態メッセージ")


class MessageInfo(BaseModel):
    """メッセージに関する情報

    Claudeエージェントとのやりとりで送受信されるメッセージの詳細を保持します。
    """

    type: str = Field(..., description="メッセージの種類")
    content: Any = Field(..., description="メッセージの内容")
    timestamp: str = Field(..., description="メッセージのタイムスタンプ")


class StatusResponse(BaseModel):
    """/status/{session_id}エンドポイント用のレスポンスモデル

    セッションの詳細状態、メッセージ履歴、結果などを含む情報を返します。
    """

    session_id: str = Field(..., description="セッションID")
    status: SessionStatus = Field(..., description="現在の状態")
    messages: List[MessageInfo] = Field(
        default_factory=list, description="メッセージのリスト"
    )
    result: Optional[Dict[str, Any]] = Field(None, description="完了時の最終結果")
    error: Optional[str] = Field(None, description="失敗時のエラーメッセージ")
    duration_ms: Optional[int] = Field(None, description="実行時間（ミリ秒）")
    total_cost_usd: Optional[float] = Field(None, description="総コスト（米ドル）")
