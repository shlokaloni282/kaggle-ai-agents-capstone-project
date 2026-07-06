def safety_check(message):

  risky_words = [
    "suicide",
    "kill myself",
    "hurt myself",
    "end of my life"
  ]

  message = message.lower()

  for word in risky_words:
    if word in message:
      return True
  return False


def safety_response():
  return """
  I'm really glad you shared this.

  I am not a replacement for professional support,
  but you deserve help and support.

  If you feel unsafe right now:
  India Emergency: 112

  You can also contact mental health helplines.
  """
