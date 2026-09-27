from criba import blackforge_pipeline, cli


def test_cli_blackforge_selection_failure_is_nonzero(monkeypatch, capsys):
    monkeypatch.setattr(
        blackforge_pipeline,
        "run_headless",
        lambda **kwargs: {"status": "SELECTION_FAILED", "ideas": []},
    )
    rc = cli.main(["blackforge", "--session-size", "4"])
    assert rc == 2
    assert "SELECTION_FAILED" in capsys.readouterr().out


def test_cli_blackforge_failure_does_not_call_configured_model(monkeypatch):
    monkeypatch.setattr(
        blackforge_pipeline,
        "run_headless",
        lambda **kwargs: {"status": "SELECTION_FAILED", "ideas": []},
    )
    monkeypatch.setattr(
        cli,
        "enhance_ideas_with_model",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("model must not run")),
    )
    assert cli.main(["blackforge", "--session-size", "4", "--use-configured-model"]) == 2
