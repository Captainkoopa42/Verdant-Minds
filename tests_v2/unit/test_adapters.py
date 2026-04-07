from verdant.adapters.text import TextAdapter


def test_text_adapter_polls_and_clears_buffer():
    adapter = TextAdapter()
    adapter.add("Water flows downhill")

    events = adapter.poll()

    assert len(events) == 1
    assert events[0].type == "text"
    assert events[0].payload == {"text": "Water flows downhill"}
    assert adapter.poll() == []
