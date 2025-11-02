"""
Claude Agent SDK APIのサンプルクライアントコード

このモジュールはClaude Agent SDK APIを使用するための
サンプルクライアント実装を提供します。
"""

import time
from typing import Dict, Optional

import requests


class ClaudeAgentClient:
    """
    Claude Agent SDK API用クライアントクラス

    Claude Agent SDKのHTTP APIとやりとりを行うためのラッパークラスです。
    エージェントの実行、状態監視、キャンセルなどの機能を提供します。
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        クライアントを初期化する

        Args:
            base_url: APIサーバーのベースURL
        """
        self.base_url = base_url

    def execute(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        permission_mode: Optional[str] = None,
        model: Optional[str] = None,
        allowed_tools: Optional[list] = None,
        disallowed_tools: Optional[list] = None,
        env: Optional[Dict[str, str]] = None,
        resume_session_id: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        新しいエージェントセッションを実行または既存セッションを再開する

        Args:
            prompt: エージェントに送信するプロンプト
            system_prompt: システムプロンプト
            permission_mode: 許可モード (default, acceptEdits, plan, bypassPermissions)
            model: 使用するモデル (sonnet, opus, haiku)
            allowed_tools: 使用を許可するツール名のリスト
            disallowed_tools: 使用を禁止するツール名のリスト
            env: 環境変数
            resume_session_id: 再開するセッションID（指定時は既存セッションを再開）
            **kwargs: その他のパラメータ

        Returns:
            セッションID
        """
        data = {"prompt": prompt}

        if system_prompt:
            data["system_prompt"] = system_prompt
        if permission_mode:
            data["permission_mode"] = permission_mode
        if model:
            data["model"] = model
        if resume_session_id:
            data["resume_session_id"] = resume_session_id

        # その他のパラメータを追加
        data.update(kwargs)

        response = requests.post(f"{self.base_url}/execute/", json=data)
        response.raise_for_status()

        result = response.json()
        return result["session_id"]

    def get_status(self, session_id: str) -> Dict:
        """
        セッションの状態を取得する

        Args:
            session_id: セッションID

        Returns:
            状態情報
        """
        response = requests.get(f"{self.base_url}/status/{session_id}")
        response.raise_for_status()
        result = response.json()

        # デバッグ: レスポンスの構造を表示
        print(f"DEBUG: get_status response type: {type(result)}")
        if isinstance(result, dict):
            print(f"DEBUG: get_status keys: {list(result.keys())}")
            if "result" in result:
                print(f"DEBUG: result field type: {type(result['result'])}")
                print(f"DEBUG: result field content: {result['result']}")
        else:
            print(f"DEBUG: Unexpected response type: {result}")

        return result

    def cleanup_sessions(self, max_age_hours: int = 0) -> Dict:
        """
        完了したセッションをクリーンアップする

        Args:
            max_age_hours: 保持するセッションの最大経過時間（デフォルト: 0時間で完了済みを全て削除）

        Returns:
            クリーンアップ結果
        """
        params = {"max_age_hours": max_age_hours}
        response = requests.delete(f"{self.base_url}/sessions/cleanup", params=params)
        response.raise_for_status()
        return response.json()

    def cancel(self, session_id: str) -> Dict:
        """
        実行中のセッションをキャンセルする

        Args:
            session_id: セッションID

        Returns:
            キャンセル結果
        """
        response = requests.post(f"{self.base_url}/cancel/{session_id}")
        response.raise_for_status()
        return response.json()

    def wait_for_completion(
        self,
        session_id: str,
        poll_interval: float = 2.0,
        timeout: Optional[float] = None,
    ) -> Dict:
        """
        セッションの完了を待つ

        Args:
            session_id: セッションID
            poll_interval: ポーリング間隔（秒）
            timeout: タイムアウト時間（秒、Noneの場合はタイムアウトなし）

        Returns:
            最終状態情報
        """
        start_time = time.time()

        while True:
            status = self.get_status(session_id)

            if status["status"] in ["completed", "error", "cancelled"]:
                return status

            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError(
                    f"セッション {session_id} が {timeout} 秒以内に完了しませんでした"
                )

            time.sleep(poll_interval)

    def list_sessions(self) -> list:
        """
        すべてのセッションを詳細情報付きで一覧表示する

        Returns:
            セッションの詳細情報リスト
        """
        response = requests.get(f"{self.base_url}/sessions/")
        response.raise_for_status()
        return response.json()


def main():
    """使用例のデモンストレーション

    Claude Agent SDK APIクライアントの様々な使用パターンを示します。
    """
    try:
        # クライアントを作成
        client = ClaudeAgentClient()
        print("サーバーへの接続をテスト中...")

        # サーバーが動作しているかテスト
        import requests

        response = requests.get(f"{client.base_url}/")
        if response.status_code == 200:
            print(f"✓ サーバーが動作中: {client.base_url}")
        else:
            print(f"⚠ サーバーエラー: {response.status_code}")
            return
    except Exception as e:
        print(f"エラー: サーバーに接続できません: {e}")
        print("FastAPIサーバーが起動しているか確認してください。")
        return

    # 例1: シンプルな実行
    print("=" * 80)
    print("例1: シンプルな実行")
    print("プロンプト：自己紹介してください。")
    print("=" * 80)

    session_id = client.execute(
        prompt="自己紹介してください。",
        system_prompt="回答は日本語で行ってください。",
        permission_mode="acceptEdits",
        model="sonnet",
    )
    print(f"Session ID: {session_id}")

    # 完了を待つ
    print("\n完了を待っています...")
    final_status = client.wait_for_completion(session_id)
    print(f"最終状態: {final_status}")

    if final_status.get("result"):
        print(f"結果: {final_status}")

    if final_status.get("error"):
        print(f"エラー: {final_status['error']}")

    print(f"実行時間: {final_status.get('duration_ms')}ms")
    print(f"コスト: ${final_status.get('total_cost_usd')}")

    # 例3: キャンセル
    print("\n" + "=" * 80)
    print("例3: キャンセル")
    print("=" * 80)

    session_id = client.execute(
        prompt="1から1000までカウントしてください",
        permission_mode="acceptEdits",
    )
    print(f"Session ID: {session_id}")

    # 少し待つ
    time.sleep(5)

    # キャンセル
    print("\nセッションをキャンセル中...")
    cancel_result = client.cancel(session_id)
    print(f"キャンセル結果: {cancel_result}")

    # すべてのセッションを一覧表示
    print("\n" + "=" * 80)
    print("すべてのセッション:")
    print("=" * 80)
    sessions = client.list_sessions()
    print(f"総セッション数: {len(sessions)}")
    for session in sessions:
        session_id = session["session_id"]
        status = session["status"]
        prompt_preview = (
            session["prompt"][:50] + "..."
            if len(session["prompt"]) > 50
            else session["prompt"]
        )
        print(f"- {session_id}: {status} | {prompt_preview}")

    # 例4: セッション再開
    print("\n" + "=" * 80)
    print("例4: セッション再開")
    print("=" * 80)

    # 最初のセッションを作成
    first_session_id = client.execute(
        prompt="私はis0383kkです。覚えてくださいね。",
        permission_mode="acceptEdits",
    )
    print(f"最初のセッションID: {first_session_id}")

    # 完了を待つ
    print("最初のセッションの完了を待っています...")
    first_status = client.wait_for_completion(first_session_id)

    if (
        first_status["status"] == "completed"
        and first_status.get("result")
        and first_status["result"].get("session_id")
    ):
        # ClaudeセッションIDが取得できた場合はセッションを再開
        print(f"ClaudeセッションID: {first_status['result']['session_id']}")
        print(f"最初の実行結果: {first_status}")

        # 同じセッションで異なるプロンプトを送信（再開）
        resumed_session_id = client.execute(
            prompt="私の名前は何だっけ？",
            resume_session_id=first_session_id,  # 既存セッションを再開
        )
        print(f"再開されたセッションID: {resumed_session_id} (同じIDのはず)")

        # 再開セッションの完了を待つ
        print("再開セッションの完了を待っています...")
        resumed_status = client.wait_for_completion(resumed_session_id)
        print(f"再開セッションの最終状態: {resumed_status}")
    else:
        print(
            "最初のセッションが完了しないか、ClaudeセッションIDが取得できませんでした"
        )

    # 例5: クリーンアップ
    print("\n" + "=" * 80)
    print("例5: 完了セッションのクリーンアップ")
    print("=" * 80)

    # クリーンアップ前のセッション数
    sessions_before = client.list_sessions()
    print(f"クリーンアップ前のセッション数: {len(sessions_before)}")

    # 完了したセッションをクリーンアップ
    cleanup_result = client.cleanup_sessions(max_age_hours=0)
    print(f"クリーンアップ結果: {cleanup_result}")

    # クリーンアップ後のセッション数
    sessions_after = client.list_sessions()
    print(f"クリーンアップ後のセッション数: {len(sessions_after)}")

    print("\nテストが完了しました！")


if __name__ == "__main__":
    main()
