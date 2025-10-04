from deep_translator import GoogleTranslator

def translate_text(text: str, target_lang: str, src_lang: str = "auto") -> str:
    if not text:
        return text
    return GoogleTranslator(source=src_lang, target=target_lang).translate(text)
