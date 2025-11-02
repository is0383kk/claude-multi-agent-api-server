"""
Claude Agent SDKセッション用のセッションマネージャー

このモジュールは、Claudeエージェントの実行セッションを管理します。
セッションの作成、状態管理、メッセージ追跡、およびクリーンアップ機能を提供します。
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, Message

from models import MessageInfo, SessionStatus


class SessionInfo:
    """セッションに関する情報を管理するクラス
    
    セッションのID、状態、設定、メッセージ履歴、結果などを保持します。
    """

    def __init__(self, session_id: str, options: ClaudeAgentOptions, prompt: str = ""):
        self.session_id = session_id
        self.status = SessionStatus.PENDING
        self.options = options
        self.prompt = prompt
        self.created_at = datetime.now()
        self.client: Optional[ClaudeSDKClient] = None
        self.messages: List[MessageInfo] = []
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.task: Optional[asyncio.Task] = None
        # Claude Agent SDKが実際に生成したセッションID（resume用）
        self.claude_session_id: Optional[str] = None

    def add_message(self, message: Message) -> None:
        """セッションにメッセージを追加する
        
        Args:
            message: 追加するメッセージオブジェクト
        """
        message_info = MessageInfo(
            type=message.__class__.__name__,
            content=self._serialize_message(message),
            timestamp=datetime.now().isoformat(),
        )
        self.messages.append(message_info)

    def _serialize_message(self, message: Message) -> Any:
        """メッセージをJSON互換形式にシリアライズする
        
        Args:
            message: シリアライズするメッセージオブジェクト
            
        Returns:
            JSON互換形式のメッセージデータ
        """
        try:
            if hasattr(message, "__dict__"):
                result = {}
                for key, value in message.__dict__.items():
                    if key.startswith("_"):
                        continue
                    try:
                        result[key] = self._serialize_value(value)
                    except Exception as e:
                        print(f"DEBUG: Error serializing key '{key}': {e}")
                        result[key] = f"<serialization_error: {str(e)}>"
                return result
            return str(message)
        except Exception as e:
            print(f"DEBUG: Error in _serialize_message: {e}")
            return f"<message_serialization_error: {str(e)}>"

    def _serialize_value(self, value: Any) -> Any:
        """Serialize a value to a JSON-compatible format"""
        try:
            if isinstance(value, (str, int, float, bool, type(None))):
                return value
            elif isinstance(value, list):
                return [self._serialize_value(v) for v in value]
            elif isinstance(value, dict):
                return {k: self._serialize_value(v) for k, v in value.items()}
            elif hasattr(value, "__dict__"):
                result = {}
                for key, val in value.__dict__.items():
                    if key.startswith("_"):
                        continue
                    try:
                        result[key] = self._serialize_value(val)
                    except Exception as e:
                        print(f"DEBUG: Error serializing nested key '{key}': {e}")
                        result[key] = f"<nested_serialization_error: {str(e)}>"
                return result
            else:
                return str(value)
        except Exception as e:
            print(f"DEBUG: Error in _serialize_value: {e}")
            return f"<value_serialization_error: {str(e)}>"

    def get_duration_ms(self) -> Optional[int]:
        """セッションの実行時間をミリ秒単位で取得する
        
        Returns:
            実行時間（ミリ秒）、または未実行の場合はNone
        """
        if self.start_time is None:
            return None
        end = self.end_time or datetime.now()
        return int((end - self.start_time).total_seconds() * 1000)


class SessionManager:
    """
Claude Agent SDKセッションのマネージャークラス

セッションの作成、実行、状態管理、キャンセル、およびクリーンアップ機能を提供します。
スレッドセーフな操作を保証するため、非同期ロックを使用します。
"""

    def __init__(self):
        self.sessions: Dict[str, SessionInfo] = {}
        self._lock = asyncio.Lock()

    def generate_session_id(self) -> str:
        """一意のセッションIDを生成する
        
        Returns:
            UUID形式の一意なセッションID
        """
        return str(uuid.uuid4())

    async def create_session(
        self, prompt: str, options: ClaudeAgentOptions, resume_session_id: Optional[str] = None
    ) -> SessionInfo:
        """新しいセッションを作成し、エージェントを開始する
        
        Args:
            prompt: エージェントに送信するプロンプト
            options: Claude Agent SDKの設定オプション
            resume_session_id: 再開するセッションID（オプション）
            
        Returns:
            作成または再開されたセッション情報
        """
        if resume_session_id:
            # 既存セッションを再開
            return await self.resume_session(resume_session_id, prompt, options)
        else:
            # 新しいセッションを作成
            session_id = self.generate_session_id()
            session = SessionInfo(session_id, options, prompt)

            async with self._lock:
                self.sessions[session_id] = session
                print(
                    f"DEBUG: Created session {session_id}, total sessions: {len(self.sessions)}"
                )

            # バックグラウンドでエージェントを開始
            session.task = asyncio.create_task(self._run_agent(session, prompt))

            return session

    async def resume_session(
        self, session_id: str, prompt: str, options: ClaudeAgentOptions
    ) -> SessionInfo:
        """既存セッションをClaude Agent SDKのresume機能で再開する
        
        既存セッションがあり、ClaudeセッションIDが記録されている場合は
        Claude Agent SDKのresume機能を使用して会話を継続します。
        
        Args:
            session_id: 再開するセッションID
            prompt: エージェントに送信するプロンプト
            options: Claude Agent SDKの設定オプション
            
        Returns:
            再開または新規作成されたセッション情報
        """
        async with self._lock:
            existing_session = self.sessions.get(session_id)
            
            if existing_session and existing_session.claude_session_id:
                # 既存セッションが存在し、ClaudeセッションIDがある場合
                if existing_session.status in [SessionStatus.RUNNING]:
                    # 実行中の場合はエラーを返す
                    raise ValueError(f"セッション {session_id} は現在実行中です")
                
                # Claude Agent SDKのresume機能を使用してセッションを再開
                print(f"DEBUG: Resuming session {session_id} with Claude session ID {existing_session.claude_session_id}")
                
                # resumeパラメータを設定
                options.resume = existing_session.claude_session_id
                
                # セッション情報を更新
                existing_session.status = SessionStatus.PENDING
                existing_session.prompt = f"{existing_session.prompt}\n\n--- セッション再開 ---\n{prompt}"
                existing_session.options = options
                existing_session.error = None
                existing_session.start_time = None
                existing_session.end_time = None
                
                # 既存のタスクがある場合はキャンセル
                if existing_session.task and not existing_session.task.done():
                    existing_session.task.cancel()
                
                session = existing_session
            else:
                # 既存セッションがないか、ClaudeセッションIDがない場合はエラー
                if existing_session:
                    raise ValueError(f"セッション {session_id} にClaudeセッションIDが記録されていません。再開できません。")
                else:
                    raise ValueError(f"セッション {session_id} が見つかりません。")
            
            print(f"DEBUG: Session {session_id} ready for resume with Claude session ID, total sessions: {len(self.sessions)}")
        
        # バックグラウンドでエージェントを開始
        session.task = asyncio.create_task(self._run_agent(session, prompt))
        
        return session

    async def _run_agent(self, session: SessionInfo, prompt: str) -> None:
        """バックグラウンドでエージェントを実行する
        
        Claude SDKクライアントを作成し、プロンプトを送信し、
        メッセージを受信してセッションを管理します。
        
        Args:
            session: 実行するセッションの情報
            prompt: エージェントに送信するプロンプト
        """
        try:
            session.status = SessionStatus.RUNNING
            session.start_time = datetime.now()

            # クライアントを作成して接続
            session.client = ClaudeSDKClient(options=session.options)
            await session.client.connect()

            # クエリを送信
            await session.client.query(prompt, session_id=session.session_id)

            # すべてのメッセージを受信
            async for message in session.client.receive_messages():
                session.add_message(message)

                # デバッグ: 詳細なメッセージ情報をログ出力
                print(f"DEBUG: Received message type: {type(message).__name__}")
                print(
                    f"DEBUG: Message attributes: {[attr for attr in dir(message) if not attr.startswith('_')]}"
                )
                if hasattr(message, "subtype"):
                    print(f"DEBUG: Message subtype: {message.subtype}")
                if hasattr(message, "is_error"):
                    print(f"DEBUG: Message is_error: {message.is_error}")
                if hasattr(message, "content"):
                    print(f"DEBUG: Message content type: {type(message.content)}")

                # メッセージ構造をより詳しく理解する
                print(f"DEBUG: Full message: {message}")
                
                # ClaudeセッションIDを早期に取得（最初のメッセージから取得できる場合）
                if not session.claude_session_id and hasattr(message, "session_id") and message.session_id:
                    session.claude_session_id = message.session_id
                    print(f"DEBUG: Early capture of Claude session ID: {session.claude_session_id}")

                # エラーメッセージかどうかをチェック
                if hasattr(message, "is_error") and message.is_error:
                    session.status = SessionStatus.ERROR
                    if hasattr(message, "result"):
                        session.error = message.result
                    else:
                        session.error = "Unknown error occurred"
                    print("DEBUG: Setting status to ERROR")
                    break

                # 様々な完了インジケーターをチェック
                is_final = False

                # final_result サブタイプをチェック
                if hasattr(message, "subtype") and message.subtype == "final_result":
                    print("DEBUG: Found final_result subtype")
                    is_final = True

                # その他の完了インジケーターをチェック
                if hasattr(message, "type") and message.type in [
                    "result",
                    "final",
                    "completion",
                ]:
                    print(f"DEBUG: Found completion type: {message.type}")
                    is_final = True

                # ターン数や実行時間の情報を持つメッセージをチェック（最終メッセージの可能性が高い）
                if hasattr(message, "num_turns") and hasattr(message, "duration_ms"):
                    print("DEBUG: Found message with turn/duration info (likely final)")
                    is_final = True

                if is_final:
                    session.status = SessionStatus.COMPLETED
                    print("DEBUG: Setting status to COMPLETED")
                    # 結果情報を保存
                    session.result = {
                        "session_id": (
                            message.session_id
                            if hasattr(message, "session_id")
                            else None
                        ),
                        "num_turns": (
                            message.num_turns if hasattr(message, "num_turns") else None
                        ),
                        "duration_ms": (
                            message.duration_ms
                            if hasattr(message, "duration_ms")
                            else None
                        ),
                        "total_cost_usd": (
                            message.total_cost_usd
                            if hasattr(message, "total_cost_usd")
                            else None
                        ),
                        "usage": session._serialize_value(message.usage) if hasattr(message, "usage") else None,
                    }
                    
                    # Claude Agent SDKが生成した実際のセッションIDを保存（resume用）
                    if hasattr(message, "session_id") and message.session_id:
                        session.claude_session_id = message.session_id
                        print(f"DEBUG: Saved Claude session ID for resume: {session.claude_session_id}")
                    
                    break

        except asyncio.CancelledError:
            session.status = SessionStatus.CANCELLED
            session.error = "Session was cancelled"
            print("DEBUG: Session cancelled")
        except Exception as e:
            session.status = SessionStatus.ERROR
            session.error = str(e)
            print(f"DEBUG: Exception in _run_agent: {e}")
            print(f"DEBUG: Exception type: {type(e)}")
            import traceback
            print(f"DEBUG: Full traceback: {traceback.format_exc()}")
        finally:
            session.end_time = datetime.now()
            print(f"DEBUG: Session ended with status: {session.status}")
            if session.client:
                try:
                    await session.client.disconnect()
                except Exception:
                    pass

    async def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """セッションIDでセッションを取得する
        
        Args:
            session_id: 取得するセッションのID
            
        Returns:
            セッション情報、または見つからない場合はNone
        """
        async with self._lock:
            return self.sessions.get(session_id)

    async def cancel_session(self, session_id: str) -> bool:
        """実行中のセッションをキャンセルする
        
        Args:
            session_id: キャンセルするセッションのID
            
        Returns:
            キャンセルが成功した場合True、そうでない場合False
        """
        async with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return False

            if session.status == SessionStatus.RUNNING:
                # クライアントを中断
                if session.client:
                    try:
                        await session.client.interrupt()
                    except Exception:
                        pass

                # タスクをキャンセル
                if session.task:
                    session.task.cancel()

                session.status = SessionStatus.CANCELLED
                session.end_time = datetime.now()
                return True

            return False

    async def list_sessions(self) -> List[str]:
        """すべてのセッションIDを一覧表示する
        
        Returns:
            セッションIDのリスト
        """
        async with self._lock:
            session_ids = list(self.sessions.keys())
            print(
                f"DEBUG: list_sessions called, found {len(session_ids)} sessions: {session_ids}"
            )
            return session_ids

    async def get_all_sessions(self) -> List[dict]:
        """すべてのセッションを詳細情報付きで取得する
        
        Returns:
            セッションの詳細情報を含む辞書のリスト
        """
        async with self._lock:
            sessions_data = []
            for session_id, session in self.sessions.items():
                session_data = {
                    "session_id": session_id,
                    "status": session.status.value,
                    "prompt": session.prompt,
                    "created_at": session.created_at.isoformat(),
                    "start_time": session.start_time.isoformat()
                    if session.start_time
                    else None,
                    "end_time": session.end_time.isoformat()
                    if session.end_time
                    else None,
                    "error": session.error,
                    "result": session.result,
                    "message_count": len(session.messages) if session.messages else 0,
                    "claude_session_id": session.claude_session_id,
                }
                sessions_data.append(session_data)

            print(f"DEBUG: get_all_sessions returning {len(sessions_data)} sessions")
            return sessions_data

    async def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """古いセッションをクリーンアップする
        
        終了時刻が指定された時間より古いセッションを削除します。
        
        Args:
            max_age_hours: 保持するセッションの最大経過時間（デフォルト: 24時間）
            
        Returns:
            削除されたセッション数
        """
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
        removed = 0

        async with self._lock:
            to_remove = []
            for session_id, session in self.sessions.items():
                if session.end_time and session.end_time.timestamp() < cutoff:
                    to_remove.append(session_id)

            for session_id in to_remove:
                del self.sessions[session_id]
                removed += 1

        return removed
