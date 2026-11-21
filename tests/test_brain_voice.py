"""Offline checks for the code that keeps JARVIS from sounding like a therapist or a chatbot.

No network, no Groq key needed: these only test the backstops in brain.py that clean up a reply
after the model writes it. Run with:  python -m pytest tests
"""

from src.jarvis import brain


# --- No coaching questions back to back (her 2026-10-27 log: 8 of 8 replies ended in a question) ---

def test_detects_that_last_reply_was_a_question():
    history = [
        {"role": "user", "content": "I don't know."},
        {"role": "assistant", "content": "Fair. What part of the job excites you?"},
    ]
    assert brain._asked_last_time(history)


def test_statement_last_time_means_a_question_is_allowed():
    history = [
        {"role": "user", "content": "They'll pay me at the end of the month."},
        {"role": "assistant", "content": "The most honest answer I've heard all week."},
    ]
    assert not brain._asked_last_time(history)


def test_empty_history_allows_a_question():
    assert not brain._asked_last_time([])


def test_trailing_question_is_dropped():
    reply = "Interviews are scary for everyone. If you could nail one thing, what would it be?"
    assert brain._without_trailing_question(reply) == "Interviews are scary for everyone."


def test_a_reply_that_is_only_a_question_is_kept():
    # Dropping it would leave JARVIS silent, which is worse than one question.
    assert brain._without_trailing_question("Wait, really?") == "Wait, really?"


def test_statement_is_left_alone():
    reply = "Ugh, that stuck feeling is the worst."
    assert brain._without_trailing_question(reply) == reply


# --- Reply clean-up before it's spoken ---

def test_stage_direction_tags_are_not_read_aloud():
    assert brain._single_reply("Okay, that's adorable.[No response needed]") == "Okay, that's adorable."


def test_voice_note_echo_is_not_read_aloud():
    assert brain._single_reply("Hmm, rough one? [voice: flatter than usual]") == "Hmm, rough one?"


def test_glued_alternative_answers_keep_only_the_first():
    assert brain._single_reply("No clue, it's newer than me.Got it, you mean the show?") == (
        "No clue, it's newer than me."
    )


def test_long_replies_are_cut_to_the_sentence_limit():
    reply = "One. Two. Three. Four. Five."
    kept = brain._single_reply(reply).split()
    assert len(kept) == brain.config.MAX_REPLY_SENTENCES


# --- Only a real goodbye switches JARVIS off ---

def test_real_goodbyes_end_the_conversation():
    for said in ["Bye Jarvis", "Okay good night", "I have to go now", "Talk to you later", "bye for now, bye-bye"]:
        assert brain._sounds_like_leaving(said), said


def test_everyday_lines_do_not_end_the_conversation():
    # Each of these once made the model call end_conversation (2026-11-11, 2026-11-14).
    for said in ["Don't give me spoilers", "Okay, I'll do it", "Hold on, let me grab water",
                 "Let's talk about something else", "Hi, hi, hi, hi"]:
        assert not brain._sounds_like_leaving(said), said
