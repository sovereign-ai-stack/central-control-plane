import unicodedata
import re
import pytest

from rag.ingestion.extraction.pdf import clean_persian_pdf_text

def test_clean_persian_pdf_text():
    sample = (
        'باكدملى ........... دراين قرار داداستتتتارت أي "شتتتود ومحرتتتوس استتتنارت أي باناب '
        'ااترارى ............... كه مطابق با يوست اين قرارداد مى باشد. ماده 2) موضوع قرار داد ارايه '
        'ادمات شتابدهى، منتورينك، سرمايهدذارى، توسعه بازار، ادمات حقوقى، مالى، زيرسااتى و '
        'ساير ادمات مورد نيازج ت رشد استارتاب ودر مقابل، مشاركت درس اب استارتاب مطابق '
        'شرايط اين قر ...'
    )
    cleaned = clean_persian_pdf_text(sample)
    
    # 1. Tatweel / repeated letters repaired
    assert "استتتتارت" not in cleaned
    assert "استارت" in cleaned
    assert "شتتتود" not in cleaned
    
    # 2. Arabic kaf/yeh repaired
    assert "منتورينك" not in cleaned
    assert "منتورینگ" in cleaned
    assert "سرمايهدذارى" not in cleaned
    assert "سرمایه‌گذاری" in cleaned
    assert "استارتاب" not in cleaned
    assert "استارتاپ" in cleaned
    assert "ادمات شتابدهى" not in cleaned
    assert "خدمات شتابدهی" in cleaned
    assert "زيرسااتى" not in cleaned
    assert "زیرساختی" in cleaned
