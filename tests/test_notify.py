from weibo_auto_signin.models import AccountCheckinResult, TopicCheckinResult
from weibo_auto_signin.notify import build_notification_message, build_notification_title


def test_build_notification_title_uses_default_prefix() -> None:
    title = build_notification_title()
    assert title.startswith("微博超话签到汇总 ")


def test_build_notification_message_includes_counts_and_account_blocks() -> None:
    results = [
        AccountCheckinResult(
            account_name="account-1",
            ok=True,
            topic_results=[
                TopicCheckinResult(
                    title="Topic A", ok=True, message="ok", experience=4, rank=1
                )
            ],
        ),
        AccountCheckinResult(
            account_name="account-2",
            ok=False,
            error_message="Failed to bootstrap session: HTTP request failed",
        ),
        AccountCheckinResult(
            account_name="account-3",
            ok=False,
            cookie_invalid=True,
            error_message="Missing required cookie keys: SUBP",
        ),
    ]

    body = build_notification_message(results)

    assert "成功账号: 1" in body
    assert "失败账号: 1" in body
    assert "Cookie 失效: 1" in body
    assert "[account-1]" in body
    assert "Topic A: +4 exp rank 1" in body
    assert "[account-2]" in body
    assert "失败: Failed to bootstrap session: HTTP request failed" in body
    assert "[account-3]" in body
    assert "Cookie 无效: Missing required cookie keys: SUBP" in body
