from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

from translation_activities import TRANSLATION_ACTIVITIES


ROOT = Path(r"C:\Users\user\Desktop\New folder (11)")
OUT = ROOT / "output"
OUT.mkdir(parents=True, exist_ok=True)
OUTPUT_DOCX = OUT / "Grade_10_Chinese_Complete_Workbook_Translation_and_Essay_Edition.docx"
COVER_IMAGE = ROOT / "assets" / "grade10_cover_students_white.png"


NAVY = "183B56"
BLUE = "2A7DB7"
SKY = "EAF4FA"
CORAL = "C9402F"
GOLD = "F2A51A"
PALE_GOLD = "FFF4D6"
INK = "253746"
MUTED = "687780"
LIGHT = "F3F6F7"
GRID = "B8C5CC"
WHITE = "FFFFFF"
GREEN = "2F8F67"
PURPLE = "6C5AA8"
MINT = "EAF7F1"
PALE_CORAL = "FCEBE7"

PAGE_WIDTH_DXA = 11906  # A4
LEFT_RIGHT_MARGIN_DXA = 936  # 0.65 in
CONTENT_WIDTH_DXA = PAGE_WIDTH_DXA - 2 * LEFT_RIGHT_MARGIN_DXA


UNITS = [
    {
        "no": 1,
        "title": "您贵姓？",
        "si": "ඔබතුමාගේ/ඔබතුමියගේ වාසගම කුමක්ද?",
        "theme": "Names, identity, nationality and work",
        "vocab": [
            ("您", "nín", "ඔබතුමා/ඔබතුමිය", "you (polite)"),
            ("贵姓", "guìxìng", "වාසගම", "honourable surname"),
            ("姓", "xìng", "වාසගම වීම", "to be surnamed"),
            ("叫", "jiào", "නම වීම/කැඳවීම", "to be called"),
            ("名字", "míngzi", "නම", "name"),
            ("谁", "shéi", "කවුද", "who"),
            ("先生", "xiānsheng", "මහතා", "Mr./sir"),
            ("老师", "lǎoshī", "ගුරුවරයා", "teacher"),
            ("学生", "xuésheng", "ශිෂ්‍යයා", "student"),
            ("中国", "Zhōngguó", "චීනය", "China"),
            ("斯里兰卡", "Sīlǐlánkǎ", "ශ්‍රී ලංකාව", "Sri Lanka"),
            ("人", "rén", "පුද්ගලයා", "person"),
            ("工作", "gōngzuò", "වැඩ කිරීම", "to work"),
            ("公司", "gōngsī", "සමාගම", "company"),
            ("大学", "dàxué", "විශ්වවිද්‍යාලය", "university"),
        ],
        "trace": [("您", 11), ("姓", 8), ("名", 6), ("字", 6), ("师", 6), ("学", 8)],
        "tone": [
            ("贵姓", ["guǐxìng", "guìxìng", "guìxíng", "guīxìng"], 2),
            ("谁", ["shén", "shěn", "shéi", "shuǐ"], 3),
            ("先生", ["xiànshēng", "xiānsheng", "xiānshěng", "xiǎnsheng"], 2),
        ],
        "grammar": [
            ("A 姓 B。", "State a surname: 我姓陈。"),
            ("A 叫 B。", "State a full/given name: 我叫安娜。"),
            ("A 是 B 吗？", "Yes/no question: 你是老师吗？"),
            ("A 是 B 还是 C？", "Choice question: 他是老师还是学生？"),
        ],
        "fill": [
            ("请问，您___姓？", "贵"),
            ("我___王，叫王小明。", "姓"),
            ("你是老师___？", "吗"),
            ("他是老师___学生？", "还是"),
            ("我___进出口公司工作。", "在"),
        ],
        "reorder": [
            ("什么 / 你 / 叫 / 名字", "你叫什么名字？"),
            ("是 / 斯里兰卡 / 我 / 人", "我是斯里兰卡人。"),
            ("工作 / 哪儿 / 你 / 在", "你在哪儿工作？"),
        ],
        "reading": "王老师：你好！请问，你叫什么名字？\n安妮：我叫安妮。我姓佩雷拉。\n王老师：你是斯里兰卡人吗？\n安妮：是，我是斯里兰卡人。我在东方学校学习汉语。",
        "rq": [
            ("安妮姓什么？", "她姓佩雷拉。"),
            ("安妮是哪国人？", "她是斯里兰卡人。"),
            ("她在哪儿学习汉语？", "她在东方学校学习汉语。"),
        ],
        "listen": "男：请问，您贵姓？ 女：我姓李，叫李红。我是汉语老师。 男：认识您很高兴。",
        "lq": [("女的姓什么？", ["王", "李", "陈"], 2), ("她做什么工作？", ["老师", "学生", "医生"], 1)],
        "dialogue": ["A：你好！请问，你___什么名字？", "B：我___ ______。", "A：你___哪国人？", "B：我是______人。", "A：认识你很高兴。", "B：我也很高兴。"],
        "task": "Make an identity card with your Chinese name, nationality, school and role. Interview two classmates and introduce one to the class.",
        "exam": [("您贵___？", ["名", "姓", "字", "人"], 2), ("我___学生。", ["是", "在", "有", "很"], 1), ("他是老师___学生？", ["吗", "呢", "还是", "也"], 3)],
        "translation": [("认识您很高兴。", "ඔබව හමුවීම සතුටක්."), ("你在哪儿工作？", "ඔබ වැඩ කරන්නේ කොහේද?")],
        "writing": "Write 40-50 Chinese characters introducing your name, nationality, school and role.",
    },
    {
        "no": 2,
        "title": "认识你很高兴",
        "si": "ඔබව හමුවීම සතුටක්",
        "theme": "Meeting people, friends and descriptions",
        "vocab": [
            ("认识", "rènshi", "හඳුනාගැනීම", "to know/meet"), ("高兴", "gāoxìng", "සතුටු", "happy"),
            ("朋友", "péngyou", "මිතුරා", "friend"), ("漂亮", "piàoliang", "ලස්සන", "pretty"),
            ("真", "zhēn", "ඇත්තෙන්ම", "really"), ("很", "hěn", "ඉතා", "very"),
            ("也", "yě", "ද/ත්", "also"), ("都", "dōu", "සියල්ලෝම", "all"),
            ("喜欢", "xǐhuan", "කැමති වීම", "to like"), ("男朋友", "nánpéngyou", "පිරිමි මිතුරා", "boyfriend"),
            ("女朋友", "nǚpéngyou", "ගැහැණු මිතුරිය", "girlfriend"), ("汉语", "Hànyǔ", "චීන භාෂාව", "Chinese"),
            ("英语", "Yīngyǔ", "ඉංග්‍රීසි", "English"), ("喝", "hē", "පානය කිරීම", "to drink"),
            ("茶", "chá", "තේ", "tea"),
        ],
        "trace": [("认", 4), ("识", 7), ("高", 10), ("兴", 6), ("朋", 8), ("友", 4)],
        "tone": [("认识", ["rēnshì", "rènshi", "rènshì", "rénshī"], 2), ("朋友", ["pèngyou", "péngyōu", "péngyou", "pēngyòu"], 3), ("漂亮", ["piáoliang", "piàoliang", "piàoliǎng", "piāoliang"], 2)],
        "grammar": [("Subject + 很 + adjective", "她很好。 Chinese adjective predicates do not need 是."), ("也", "Adds 'also': 我也学习汉语。"), ("都", "Refers to all members: 我们都喜欢茶。"), ("不 + verb/adjective", "Negation: 他不忙。")],
        "fill": [("认识你，我___高兴。", "很"), ("我学习汉语，她___学习汉语。", "也"), ("我们___喜欢王老师。", "都"), ("她___漂亮。", "真"), ("我___喝咖啡。", "不")],
        "reorder": [("很 / 认识 / 高兴 / 你", "认识你很高兴。"), ("都 / 我们 / 他 / 喜欢", "我们都喜欢他。"), ("也 / 汉语 / 她 / 学习", "她也学习汉语。")],
        "reading": "这是我的朋友美玲。她是中国人，也是学生。她学习英语，我学习汉语。我们都喜欢喝茶。美玲很漂亮，也很高兴。",
        "rq": [("美玲是哪国人？", "她是中国人。"), ("美玲学习什么？", "她学习英语。"), ("她们都喜欢喝什么？", "她们都喜欢喝茶。")],
        "listen": "女：这是谁？ 男：这是我的朋友大卫。他是学生。 女：他也学习汉语吗？ 男：是，我们都学习汉语。",
        "lq": [("大卫是谁？", ["老师", "朋友", "哥哥"], 2), ("他们学习什么？", ["英语", "日语", "汉语"], 3)],
        "dialogue": ["A：这___谁？", "B：这是我的___ ______。", "A：他/她是哪国人？", "B：他/她是______人。", "A：他/她怎么样？", "B：他/她很______。"],
        "task": "Draw a simple portrait box for a friend. Add four Chinese labels, then introduce the friend using 也 and 都.",
        "exam": [("认识你___高兴。", ["很", "都", "在", "是"], 1), ("我们___是学生。", ["真", "都", "不在", "谁"], 2), ("她学习汉语，我___学习汉语。", ["也", "很", "吗", "的"], 1)],
        "translation": [("我们都很喜欢他。", "අපි සියලුදෙනාම ඔහුට ඉතා කැමතියි."), ("她也学习汉语。", "ඇයත් චීන භාෂාව ඉගෙනගන්නවා.")],
        "writing": "Write 40-50 Chinese characters about a friend. Use 很, 也 and 都 at least once.",
    },
    {
        "no": 3,
        "title": "你家有几口人？",
        "si": "ඔබේ පවුලේ කීදෙනෙක් සිටීද?",
        "theme": "Family, age, numbers and measure words",
        "vocab": [
            ("家", "jiā", "පවුල/නිවස", "family/home"), ("有", "yǒu", "තිබීම", "to have"),
            ("几", "jǐ", "කීයක්ද", "how many (small)"), ("口", "kǒu", "කට/පවුල් ඒකකය", "measure for family"),
            ("爸爸", "bàba", "තාත්තා", "father"), ("妈妈", "māma", "අම්මා", "mother"),
            ("哥哥", "gēge", "වැඩිමහල් සහෝදරයා", "elder brother"), ("姐姐", "jiějie", "වැඩිමහල් සහෝදරිය", "elder sister"),
            ("弟弟", "dìdi", "බාල සහෝදරයා", "younger brother"), ("妹妹", "mèimei", "බාල සහෝදරිය", "younger sister"),
            ("孩子", "háizi", "ළමයා", "child"), ("岁", "suì", "වයස අවුරුදු", "years old"),
            ("多大", "duōdà", "වයස කීයද", "how old"), ("可爱", "kě'ài", "හුරුබුහුටි", "cute"),
            ("多少", "duōshao", "කීයක්ද", "how many/how much"),
        ],
        "trace": [("家", 10), ("有", 6), ("口", 3), ("人", 2), ("姐", 8), ("岁", 6)],
        "tone": [("多少", ["duōshǎo", "duōshao", "duōshào", "duóshao"], 2), ("可爱", ["kē'ǎi", "kè'ái", "kě'ài", "ké'ài"], 3), ("姐姐", ["jièjie", "jiějie", "jiějiě", "jiējie"], 2)],
        "grammar": [("Place/person + 有 + noun", "我家有四口人。"), ("没有", "Negative of 有: 我没有哥哥。"), ("几 + measure word + noun", "你家有几口人？"), ("Number + 岁", "我十五岁。")],
        "fill": [("你家有几___人？", "口"), ("我___一个姐姐。", "有"), ("我没有哥哥，___一个弟弟。", "有"), ("你今年多___？", "大"), ("妹妹十二___。", "岁")],
        "reorder": [("几 / 你 / 人 / 家 / 口 / 有", "你家有几口人？"), ("岁 / 姐姐 / 十六 / 我", "我姐姐十六岁。"), ("哥哥 / 没有 / 我", "我没有哥哥。")],
        "reading": "我家有五口人：爸爸、妈妈、哥哥、妹妹和我。爸爸四十五岁，妈妈四十二岁。哥哥十八岁，是学生。妹妹十岁，很可爱。我今年十五岁。",
        "rq": [("他家有几口人？", "他家有五口人。"), ("哥哥多大？", "哥哥十八岁。"), ("谁很可爱？", "妹妹很可爱。")],
        "listen": "女：你家有几口人？ 男：四口人。爸爸、妈妈、姐姐和我。 女：你姐姐多大？ 男：她二十岁。",
        "lq": [("男的家有几口人？", ["三口", "四口", "五口"], 2), ("姐姐多大？", ["十二岁", "十五岁", "二十岁"], 3)],
        "dialogue": ["A：你家有___口人？", "B：我家有___口人。", "A：他们是谁？", "B：他们是______。", "A：你的______多大？", "B：他/她______岁。"],
        "task": "Make a family tree with names and ages. Ask a partner three questions using 几, 谁 and 多大.",
        "exam": [("我家有四___人。", ["个", "口", "本", "张"], 2), ("你今年___？", ["多少", "几口", "多大", "谁"], 3), ("我___弟弟。", ["没有", "不是", "不很", "没是"], 1)],
        "translation": [("你家有几口人？", "ඔබේ පවුලේ කීදෙනෙක් සිටීද?"), ("我妹妹十二岁。", "මගේ බාල සහෝදරියට වයස අවුරුදු දොළහයි.")],
        "writing": "Write 50 Chinese characters about your family. Include family size and two ages.",
    },
    {
        "no": 4,
        "title": "这张地图是僧伽罗语的",
        "si": "මේ සිතියම සිංහල භාෂාවෙන්",
        "theme": "Objects, languages, numbers and measure words",
        "vocab": [
            ("这", "zhè", "මේ", "this"), ("那", "nà", "අර", "that"), ("张", "zhāng", "පත්‍ර සඳහා මිනුම් පදය", "measure for flat objects"),
            ("地图", "dìtú", "සිතියම", "map"), ("本", "běn", "පොත් සඳහා මිනුම් පදය", "measure for books"),
            ("词典", "cídiǎn", "ශබ්දකෝෂය", "dictionary"), ("书", "shū", "පොත", "book"),
            ("僧伽罗语", "Sēngqiéluóyǔ", "සිංහල භාෂාව", "Sinhala language"), ("英语", "Yīngyǔ", "ඉංග්‍රීසි", "English"),
            ("的", "de", "සම්බන්ධක/අයිතිය", "possessive particle"), ("学校", "xuéxiào", "පාසල", "school"),
            ("学生", "xuésheng", "ශිෂ්‍යයා", "student"), ("非常", "fēicháng", "ඉතාම", "extremely"),
            ("百", "bǎi", "සියය", "hundred"), ("万", "wàn", "දසදහස", "ten thousand"),
        ],
        "trace": [("地", 6), ("图", 8), ("书", 4), ("张", 7), ("本", 5), ("语", 9)],
        "tone": [("地图", ["dítú", "dìtú", "dītú", "dìtǔ"], 2), ("词典", ["cídiàn", "cìdiǎn", "cídiǎn", "cīdiǎn"], 1), ("非常", ["fēichǎng", "fēicháng", "fěicháng", "fèicháng"], 2)],
        "grammar": [("Demonstrative + measure + noun", "这张地图 / 那本词典"), ("Noun + 的", "这是我的书。"), ("Numeral + measure + noun", "三本书、两张地图"), ("Exact large numbers", "二百、三千、两万")],
        "fill": [("这___地图是中国的。", "张"), ("我有两___词典。", "本"), ("这是我___书。", "的"), ("我们学校有两___多个学生。", "万"), ("那___什么书？", "是")],
        "reorder": [("地图 / 张 / 这 / 的 / 是 / 中国", "这张地图是中国的。"), ("本 / 我 / 词典 / 有 / 两", "我有两本词典。"), ("书 / 谁 / 的 / 是 / 这", "这是谁的书？")],
        "reading": "我们学校很大，有两万多个学生。一百多个学生学习汉语。图书馆里有汉语书、英语书和僧伽罗语词典。我有一本汉语词典和两张中国地图。",
        "rq": [("学校有多少学生？", "有两万多个学生。"), ("多少学生学习汉语？", "一百多个学生学习汉语。"), ("他有几张中国地图？", "他有两张中国地图。")],
        "listen": "男：这是谁的地图？ 女：是我的，是一张中国地图。 男：那本词典也是你的吗？ 女：不是，是王老师的。",
        "lq": [("地图是谁的？", ["男的", "女的", "王老师的"], 2), ("词典是谁的？", ["王老师的", "学生的", "女的"], 1)],
        "dialogue": ["A：这___什么？", "B：这是一___ ______。", "A：这是___的吗？", "B：是，这是我的。/ 不是。", "A：那本词典是什么语的？", "B：是______语的。"],
        "task": "Label a desk picture using 这/那 and the correct measure word. Exchange objects with a partner and ask 谁的.",
        "exam": [("一___中国地图", ["本", "张", "口", "件"], 2), ("两___汉语书", ["本", "张", "条", "口"], 1), ("这是我___词典。", ["地", "得", "的", "也"], 3)],
        "translation": [("这是谁的书？", "මේක කාගේ පොතද?"), ("我有两张中国地图。", "මට චීන සිතියම් දෙකක් තියෙනවා.")],
        "writing": "Describe five objects in your classroom using 这/那, 的 and measure words.",
    },
    {
        "no": 5,
        "title": "能不能试一试？",
        "si": "ඇඳලා බලන්න පුළුවන්ද?",
        "theme": "Shopping, clothing, colours and Chinese currency",
        "vocab": [
            ("能", "néng", "හැකි වීම", "can"), ("试", "shì", "උත්සාහ/අත්හදා බැලීම", "to try"), ("衬衫", "chènshān", "කමිසය", "shirt"),
            ("裤子", "kùzi", "කලිසම", "trousers"), ("衣服", "yīfu", "ඇඳුම්", "clothes"), ("件", "jiàn", "ඇඳුම් සඳහා මිනුම් පදය", "measure for clothing"),
            ("条", "tiáo", "දිගු දේ සඳහා මිනුම් පදය", "measure for long items"), ("颜色", "yánsè", "පාට", "colour"),
            ("红", "hóng", "රතු", "red"), ("蓝", "lán", "නිල්", "blue"), ("白", "bái", "සුදු", "white"), ("黑", "hēi", "කළු", "black"),
            ("便宜", "piányi", "ලාභ", "cheap"), ("贵", "guì", "මිල අධික", "expensive"), ("元", "yuán", "යුවාන්", "yuan"),
        ],
        "trace": [("能", 10), ("试", 8), ("衣", 6), ("色", 6), ("买", 6), ("钱", 10)],
        "tone": [("衬衫", ["chénshān", "chènshān", "chěnshān", "chènshǎn"], 2), ("便宜", ["piānyì", "piányi", "piànyi", "piǎnyí"], 2), ("颜色", ["yànsè", "yánsè", "yānsè", "yǎnsé"], 2)],
        "grammar": [("能不能 + verb", "能不能试一试？"), ("可以 + verb + 吗", "可以看看吗？"), ("多少钱", "这件衬衫多少钱？"), ("太 + adjective + 了", "太贵了！")],
        "fill": [("我能不能___一试？", "试"), ("这___衬衫多少钱？", "件"), ("我买一___黑裤子。", "条"), ("一百元？太___了！", "贵"), ("这件衣服很便宜，___很漂亮。", "也")],
        "reorder": [("多少钱 / 衬衫 / 这件", "这件衬衫多少钱？"), ("试 / 能不能 / 一试 / 我", "我能不能试一试？"), ("蓝色 / 我 / 的 / 喜欢", "我喜欢蓝色的。")],
        "reading": "售货员：你要买什么？\n玛丽：我想买一件白衬衫。\n售货员：这件怎么样？八十元。\n玛丽：有一点儿贵。那件蓝色的呢？\n售货员：六十元。\n玛丽：好，我能不能试一试？",
        "rq": [("玛丽想买什么？", "她想买一件衬衫。"), ("白衬衫多少钱？", "八十元。"), ("她最后想试什么颜色的？", "蓝色的。")],
        "listen": "女：这条黑裤子多少钱？ 男：九十元。 女：太贵了。那条蓝色的呢？ 男：七十元。 女：好，我买蓝色的。",
        "lq": [("黑裤子多少钱？", ["七十元", "八十元", "九十元"], 3), ("她买什么颜色的？", ["黑色", "蓝色", "白色"], 2)],
        "dialogue": ["A：你要买___？", "B：我想买一___ ______。", "A：这件/条怎么样？", "B：多少钱？", "A：______元。", "B：能不能便宜一点儿？"],
        "task": "Create three price tags in yuan. Role-play customer and shop assistant, changing colour, measure word and price each round.",
        "exam": [("一___衬衫", ["件", "条", "张", "本"], 1), ("一___裤子", ["件", "条", "口", "个"], 2), ("这件衣服___钱？", ["几", "多少", "多大", "谁"], 2)],
        "translation": [("这件衬衫多少钱？", "මේ කමිසය යුවාන් කීයද?"), ("太贵了！", "ගොඩක් මිල අධිකයි!")],
        "writing": "Write a 6-line shop dialogue. Include a colour, price, measure word and 能不能.",
    },
    {
        "no": 6,
        "title": "明天打算干什么？",
        "si": "හෙට මොනවා කරන්නද අදහස?",
        "theme": "Plans, days, dates and clock time",
        "vocab": [
            ("明天", "míngtiān", "හෙට", "tomorrow"), ("今天", "jīntiān", "අද", "today"), ("昨天", "zuótiān", "ඊයේ", "yesterday"),
            ("打算", "dǎsuàn", "අදහස් කිරීම", "to plan"), ("干", "gàn", "කිරීම", "to do"), ("休息", "xiūxi", "විවේක ගැනීම", "to rest"),
            ("看电影", "kàn diànyǐng", "චිත්‍රපටයක් බැලීම", "watch a film"), ("学习", "xuéxí", "ඉගෙනීම", "study"),
            ("一起", "yìqǐ", "එකට", "together"), ("星期", "xīngqī", "සතියේ දිනය", "week"), ("月", "yuè", "මාසය", "month"),
            ("号", "hào", "දිනය", "date number"), ("点", "diǎn", "පැය", "o'clock"), ("分", "fēn", "විනාඩිය", "minute"), ("时候", "shíhou", "වේලාව", "time/moment"),
        ],
        "trace": [("明", 8), ("天", 4), ("打", 5), ("算", 14), ("点", 9), ("分", 4)],
        "tone": [("打算", ["dásuàn", "dǎsuàn", "dǎsuān", "dàsuān"], 2), ("休息", ["xiǔxǐ", "xiùxì", "xiūxi", "xiūxí"], 3), ("电影", ["diānyīng", "diànyǐng", "diǎnyǐng", "diànyīng"], 2)],
        "grammar": [("Time + subject + action", "明天我去学校。"), ("打算/想/要 + verb", "我打算看电影。"), ("Date", "八月二十五号 / 二〇二六年八月二十五日"), ("Clock time", "上午九点半 / 下午三点十五分")],
        "fill": [("明天你打算___什么？", "干"), ("我想___电影。", "看"), ("我们___去学校。", "一起"), ("今天八月二十五___。", "号"), ("电影下午三___开始。", "点")],
        "reorder": [("什么 / 明天 / 打算 / 你 / 干", "明天你打算干什么？"), ("一起 / 我们 / 电影 / 看", "我们一起看电影。"), ("九点 / 汉语课 / 上午 / 开始", "汉语课上午九点开始。")],
        "reading": "今天是星期五。明天上午我打算在家学习汉语，十点休息。下午三点我和朋友一起看电影。星期天我不出去，我在家看书。",
        "rq": [("今天星期几？", "星期五。"), ("明天上午他做什么？", "在家学习汉语。"), ("什么时候看电影？", "明天下午三点。")],
        "listen": "男：明天是八月二十六号，星期三。上午九点我们上汉语课，下午两点去图书馆。女：晚上呢？男：晚上七点看电影。",
        "lq": [("上午几点上汉语课？", ["八点", "九点", "十点"], 2), ("晚上做什么？", ["看电影", "去图书馆", "休息"], 1)],
        "dialogue": ["A：明天是几月几___？", "B：明天是___月___号。", "A：你打算干什么？", "B：我打算______。", "A：几点？", "B：______点。"],
        "task": "Complete a one-day timetable with three times. Ask a partner about the plan, then report it using 他/她.",
        "exam": [("明天你打算___什么？", ["做", "干", "是", "有"], 2), ("下午三___", ["号", "月", "点", "岁"], 3), ("八月二十五___", ["分", "号", "点", "年"], 2)],
        "translation": [("明天下午三点我们一起看电影。", "හෙට පස්වරු තුනට අපි එකට චිත්‍රපටයක් බලනවා."), ("今天是星期五。", "අද සිකුරාදායි.")],
        "writing": "Write your plan for one day with a date and at least three times/actions.",
    },
    {
        "no": 7,
        "title": "你什么时候回来？",
        "si": "ඔබ නැවත එන්නේ කවදාද?",
        "theme": "Travel, return times and alternatives",
        "vocab": [
            ("什么时候", "shénme shíhou", "කවදාද", "when"), ("回来", "huílai", "නැවත පැමිණීම", "come back"),
            ("去", "qù", "යෑම", "go"), ("旅行", "lǚxíng", "සංචාරය", "travel"), ("以前", "yǐqián", "පෙර", "before"),
            ("以后", "yǐhòu", "පසු", "after"), ("或者", "huòzhě", "හෝ", "or (statement)"), ("还是", "háishi", "හෝ", "or (question)"),
            ("火车", "huǒchē", "දුම්රිය", "train"), ("飞机", "fēijī", "ගුවන් යානය", "airplane"),
            ("上午", "shàngwǔ", "පෙරවරු", "morning"), ("下午", "xiàwǔ", "පස්වරු", "afternoon"),
            ("从", "cóng", "සිට", "from"), ("到", "dào", "දක්වා", "to"), ("先", "xiān", "පළමුව", "first"),
        ],
        "trace": [("旅", 10), ("行", 6), ("回", 6), ("来", 7), ("火", 4), ("车", 4)],
        "tone": [("旅行", ["lùxíng", "lǚxíng", "lǔxíng", "lǚxìng"], 2), ("或者", ["huǒzhě", "huózhè", "huòzhě", "huōzhě"], 3), ("以前", ["yīqiān", "yǐqián", "yíqián", "yìqiàn"], 2)],
        "grammar": [("什么时候", "Ask time: 你什么时候回来？"), ("还是", "Choice question: 坐火车还是飞机？"), ("或者", "Statement choice: 坐火车或者飞机都可以。"), ("从...到...", "从科伦坡到康提。")],
        "fill": [("你___时候回来？", "什么"), ("你坐火车___飞机？", "还是"), ("我们星期六___星期天去。", "或者"), ("我___北京到上海。", "从"), ("下午五点___学校。", "回来")],
        "reorder": [("回来 / 你 / 什么时候", "你什么时候回来？"), ("火车 / 还是 / 飞机 / 坐 / 你", "你坐火车还是飞机？"), ("到 / 从 / 上海 / 北京", "从北京到上海。")],
        "reading": "下个月我去中国旅行。我先坐飞机到北京，在北京学习一个星期。以后坐火车去上海。八月十八号上午回斯里兰卡。朋友问我坐火车还是飞机回来，我说坐飞机。",
        "rq": [("他什么时候去中国？", "下个月。"), ("他在北京做什么？", "学习一个星期。"), ("他什么时候回斯里兰卡？", "八月十八号上午。")],
        "listen": "女：你什么时候去康提？ 男：星期六上午。 女：坐火车还是汽车？ 男：坐火车。星期天下午五点回来。",
        "lq": [("男的什么时候去康提？", ["星期五", "星期六上午", "星期天下午"], 2), ("他怎么去？", ["坐火车", "坐飞机", "坐汽车"], 1)],
        "dialogue": ["A：你什么时候去______？", "B：我___月___号去。", "A：坐火车___飞机？", "B：我坐______。", "A：什么时候回来？", "B：______回来。"],
        "task": "Draw a two-stop travel line using 从 and 到. Tell a partner the dates, transport and return time.",
        "exam": [("你___时候回来？", ["怎么", "什么", "哪儿", "多少"], 2), ("坐火车___飞机？", ["或者", "还是", "可是", "也"], 2), ("我星期六___星期天去。", ["还是", "或者", "吗", "呢"], 2)],
        "translation": [("你坐火车还是飞机？", "ඔබ යන්නේ දුම්රියෙන්ද ගුවන් යානයෙන්ද?"), ("我星期天下午回来。", "මම ඉරිදා පස්වරුවේ නැවත එනවා.")],
        "writing": "Write a 50-character travel plan using 从...到..., a date, transport and return time.",
    },
    {
        "no": 8,
        "title": "附近有没有银行？",
        "si": "අසල බැංකුවක් තිබේද?",
        "theme": "Places, locations and directions",
        "vocab": [
            ("附近", "fùjìn", "අසල", "nearby"), ("银行", "yínháng", "බැංකුව", "bank"), ("有没有", "yǒu méiyǒu", "තියෙනවද නැද්ද", "is there/are there"),
            ("哪儿", "nǎr", "කොහේද", "where"), ("在", "zài", "හි සිටීම", "be at"), ("旁边", "pángbiān", "අසල පැත්තේ", "beside"),
            ("前面", "qiánmian", "ඉදිරිපස", "in front"), ("后面", "hòumian", "පිටුපස", "behind"),
            ("左边", "zuǒbian", "වම් පැත්ත", "left side"), ("右边", "yòubian", "දකුණු පැත්ත", "right side"),
            ("对面", "duìmiàn", "ඉදිරිපිට", "opposite"), ("医院", "yīyuàn", "රෝහල", "hospital"),
            ("邮局", "yóujú", "තැපැල් කාර්යාලය", "post office"), ("左转", "zuǒzhuǎn", "වමට හැරෙන්න", "turn left"),
            ("右转", "yòuzhuǎn", "දකුණට හැරෙන්න", "turn right"),
        ],
        "trace": [("附", 7), ("近", 7), ("银", 11), ("行", 6), ("左", 5), ("右", 5)],
        "tone": [("附近", ["fǔjìn", "fùjìn", "fújìn", "fūjīn"], 2), ("银行", ["yìnháng", "yǐnháng", "yínháng", "yīnháng"], 3), ("旁边", ["pàngbiān", "pángbiān", "pángbiǎn", "pāngbiān"], 2)],
        "grammar": [("Place + 有 + object", "学校旁边有一家银行。"), ("Object + 在 + location", "银行在邮局对面。"), ("有没有", "附近有没有医院？"), ("Direction sequence", "一直走，然后左转。")],
        "fill": [("附近___没有银行？", "有"), ("银行___邮局对面。", "在"), ("学校旁___有商店。", "边"), ("一直走，然后___转。", "左"), ("医院在银行的___面。", "后")],
        "reorder": [("有没有 / 附近 / 银行", "附近有没有银行？"), ("对面 / 邮局 / 银行 / 在", "银行在邮局对面。"), ("左转 / 然后 / 一直走", "一直走，然后左转。")],
        "reading": "我们学校附近有一家银行。银行左边是邮局，右边是商店。医院在银行后面。你从学校出来一直走，在第一个路口右转，就能看见银行。",
        "rq": [("学校附近有什么？", "有一家银行。"), ("邮局在哪儿？", "在银行左边。"), ("怎么从学校到银行？", "一直走，在第一个路口右转。")],
        "listen": "女：请问，附近有没有邮局？ 男：有。一直走，第二个路口左转。邮局在银行旁边。 女：谢谢。",
        "lq": [("女的找什么？", ["银行", "邮局", "医院"], 2), ("在哪个路口左转？", ["第一个", "第二个", "第三个"], 2)],
        "dialogue": ["A：请问，附近有___有银行？", "B：有。", "A：银行在哪儿？", "B：在______旁边/对面。", "A：怎么走？", "B：一直走，然后___转。"],
        "task": "Use the blank street grid to place a bank, post office, school and hospital. Give a partner directions to two places.",
        "exam": [("附近___没有银行？", ["有", "在", "是", "很"], 1), ("银行___邮局对面。", ["有", "是", "在", "去"], 3), ("一直走，然后___转。", ["上", "左", "前", "外"], 2)],
        "translation": [("银行在邮局对面。", "බැංකුව තැපැල් කාර්යාලය ඉදිරිපිටයි."), ("一直走，然后右转。", "කෙළින්ම ගොස් පසුව දකුණට හැරෙන්න.")],
        "writing": "Write directions from your school to a nearby place in 5-6 Chinese sentences.",
    },
]


EXTENSION_NOTES = {
    1: (
        "In Chinese names, the family name normally comes first. 您 is a polite form of 你.",
        ["Greet a classmate politely.", "Ask for a Chinese name.", "Ask nationality.", "Introduce your partner."],
    ),
    2: (
        "认识你很高兴 is a friendly expression used when meeting someone for the first time.",
        ["Introduce a friend.", "Give one positive description.", "Say what both of you like.", "Use 也 in a new sentence."],
    ),
    3: (
        "口 is the usual measure word when counting members of a family.",
        ["Ask about family size.", "Ask a person's age.", "Say who is older.", "Describe one family member."],
    ),
    4: (
        "Chinese nouns often need a measure word: 一本书, 一张地图, 一个学生.",
        ["Point to a book and describe it.", "Ask whose object it is.", "Use a number above 100.", "Name two languages."],
    ),
    5: (
        "元 is the everyday unit used for prices in China. Measure words change with the item.",
        ["Ask a price.", "Ask to try an item.", "Choose a colour.", "Say that something is too expensive."],
    ),
    6: (
        "Chinese dates move from larger to smaller units: year, month, date; time uses 点 and 分.",
        ["Say today's date.", "Tell the time.", "Invite a friend.", "Explain tomorrow's plan."],
    ),
    7: (
        "还是 is used inside a choice question; 或者 joins alternatives in a statement.",
        ["Ask when someone returns.", "Choose train or plane.", "Say a travel route.", "Describe a short trip."],
    ),
    8: (
        "When giving directions, start with 一直走 and add 左转 or 右转 at the correct junction.",
        ["Ask for a bank.", "Say where a place is.", "Give two direction steps.", "Check that your partner understood."],
    ),
}


REVISION_MEASURE_ITEMS = [
    ("一___学生", "个"), ("五___人", "口"), ("两___书", "本"),
    ("三___地图", "张"), ("一___衬衫", "件"), ("两___裤子", "条"),
    ("一___银行", "家"), ("四___词典", "本"),
]


REVISION_REPAIR_ITEMS = [
    ("我是在学生。", "我是学生。"),
    ("她很是漂亮。", "她很漂亮。"),
    ("你家有几人 口？", "你家有几口人？"),
    ("我有两张书。", "我有两本书。"),
    ("这条衬衫多少钱？", "这件衬衫多少钱？"),
    ("明天你什么打算干？", "明天你打算干什么？"),
    ("你坐火车或者飞机？", "你坐火车还是飞机？"),
    ("银行有邮局对面。", "银行在邮局对面。"),
]


ESSAY_TOPICS = [
    {
        "title": "我的汉语老师", "english": "My Chinese Teacher",
        "prompts": ["老师叫什么名字？", "老师是哪国人？", "老师怎么样？", "你为什么喜欢他/她？"],
        "words": "老师  汉语  叫  姓  很  也  喜欢  学习",
        "starters": ["我的汉语老师叫……", "他/她很……，也很……"],
    },
    {
        "title": "我的家", "english": "My Family",
        "prompts": ["你家有几口人？", "他们是谁？", "他们多大？", "你们喜欢做什么？"],
        "words": "家  有  口  爸爸  妈妈  哥哥  姐姐  喜欢",
        "starters": ["我家有……口人。", "我们都喜欢……"],
    },
    {
        "title": "我的朋友", "english": "My Friend",
        "prompts": ["朋友叫什么名字？", "朋友是哪国人？", "朋友怎么样？", "你们一起做什么？"],
        "words": "朋友  认识  高兴  漂亮  可爱  学生  也  一起",
        "starters": ["这是我的朋友……", "我们都喜欢……"],
    },
    {
        "title": "我的中国朋友", "english": "My Chinese Friend",
        "prompts": ["朋友叫什么名字？", "他/她住在哪儿？", "他/她学习什么？", "你们怎么认识的？"],
        "words": "中国  朋友  认识  汉语  英语  学习  喜欢  一起",
        "starters": ["我有一个中国朋友。", "他/她叫……，住在……"],
    },
    {
        "title": "我的学校", "english": "My School",
        "prompts": ["学校叫什么名字？", "学校在哪儿？", "学校大不大？", "你在学校学习什么？"],
        "words": "学校  学生  老师  学习  汉语  大  漂亮  附近",
        "starters": ["我的学校叫……", "学校有很多……"],
    },
    {
        "title": "我的姐姐", "english": "My Elder Sister",
        "prompts": ["姐姐叫什么名字？", "姐姐多大？", "姐姐做什么？", "姐姐喜欢什么？"],
        "words": "姐姐  岁  学生  工作  漂亮  可爱  喜欢  也",
        "starters": ["我有一个姐姐。", "她今年……岁。"],
    },
    {
        "title": "我", "english": "About Me",
        "prompts": ["你叫什么名字？", "你是哪国人？", "你多大？", "你喜欢做什么？"],
        "words": "我  叫  姓  岁  学生  学校  喜欢  学习",
        "starters": ["我叫……，姓……", "我今年……岁。"],
    },
    {
        "title": "学习汉语", "english": "Learning Chinese",
        "prompts": ["你在哪儿学习汉语？", "谁教你汉语？", "汉语怎么样？", "你怎么练习汉语？"],
        "words": "学习  汉语  老师  学校  喜欢  说  写  读",
        "starters": ["我在……学习汉语。", "我觉得汉语……"],
    },
    {
        "title": "我妈妈", "english": "My Mother",
        "prompts": ["妈妈叫什么名字？", "妈妈多大？", "妈妈做什么工作？", "妈妈喜欢什么？"],
        "words": "妈妈  名字  岁  工作  公司  漂亮  喜欢  家",
        "starters": ["我妈妈叫……", "她在……工作。"],
    },
    {
        "title": "我们班", "english": "Our Class",
        "prompts": ["你们班有多少学生？", "谁教你们？", "同学们怎么样？", "你们一起学习什么？"],
        "words": "我们  班  学生  老师  都  一起  学习  朋友",
        "starters": ["我们班有……个学生。", "我们都喜欢……"],
    },
]


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=80, start=100, bottom=80, end=100):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for m, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{m}"))
        if node is None:
            node = OxmlElement(f"w:{m}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_borders(table, color=GRID, size=6):
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = borders.find(qn(f"w:{edge}"))
        if tag is None:
            tag = OxmlElement(f"w:{edge}")
            borders.append(tag)
        tag.set(qn("w:val"), "single")
        tag.set(qn("w:sz"), str(size))
        tag.set(qn("w:space"), "0")
        tag.set(qn("w:color"), color)


def set_table_geometry(table, widths):
    total = sum(widths)
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    table.autofit = False
    tbl_pr = table._tbl.tblPr
    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.append(tbl_w)
    tbl_w.set(qn("w:w"), str(total))
    tbl_w.set(qn("w:type"), "dxa")
    tbl_ind = tbl_pr.find(qn("w:tblInd"))
    if tbl_ind is None:
        tbl_ind = OxmlElement("w:tblInd")
        tbl_pr.append(tbl_ind)
    tbl_ind.set(qn("w:w"), "100")
    tbl_ind.set(qn("w:type"), "dxa")
    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths:
        col = OxmlElement("w:gridCol")
        col.set(qn("w:w"), str(width))
        grid.append(col)
    for row in table.rows:
        for idx, cell in enumerate(row.cells):
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_w = tc_pr.find(qn("w:tcW"))
            if tc_w is None:
                tc_w = OxmlElement("w:tcW")
                tc_pr.append(tc_w)
            tc_w.set(qn("w:w"), str(widths[min(idx, len(widths) - 1)]))
            tc_w.set(qn("w:type"), "dxa")
            set_cell_margins(cell)


def font_run(run, size=10.5, bold=False, color=INK, italic=False, name="Arial"):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = RGBColor.from_string(color)
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.get_or_add_rFonts()
    rfonts.set(qn("w:ascii"), name)
    rfonts.set(qn("w:hAnsi"), name)
    rfonts.set(qn("w:eastAsia"), "SimSun")
    rfonts.set(qn("w:cs"), "Nirmala UI")
    return run


def style_paragraph(p, before=0, after=4, line=1.08, align=None, keep=False):
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    if align is not None:
        p.alignment = align
    pf.keep_with_next = keep
    return p


def add_para(doc, text="", size=10.5, bold=False, color=INK, italic=False, before=0, after=4, align=None, keep=False):
    p = doc.add_paragraph()
    style_paragraph(p, before, after, 1.08, align, keep)
    font_run(p.add_run(text), size=size, bold=bold, color=color, italic=italic)
    return p


def add_page_field(paragraph):
    run = paragraph.add_run()
    fld_char = OxmlElement("w:fldChar")
    fld_char.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([fld_char, instr, separate, text, end])
    font_run(run, size=8.5, color=MUTED)


def add_page_break(doc):
    p = doc.add_paragraph()
    p.add_run().add_break(WD_BREAK.PAGE)


def add_banner(doc, label, title, subtitle=None):
    table = doc.add_table(rows=1, cols=2)
    label_width = 2500
    set_table_geometry(table, [label_width, CONTENT_WIDTH_DXA - label_width])
    set_table_borders(table, color=WHITE, size=0)
    left, right = table.rows[0].cells
    set_cell_shading(left, CORAL)
    set_cell_shading(right, SKY)
    left.vertical_alignment = right.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    p = left.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    label_size = 8.5 if len(label) > 12 else (9.5 if len(label) > 8 else 11)
    font_run(p.add_run(label), label_size, True, WHITE)
    p = right.paragraphs[0]
    font_run(p.add_run(title), 17, True, NAVY)
    if subtitle:
        p.add_run("\n")
        font_run(p.add_run(subtitle), 9.5, False, MUTED)
    add_para(doc, "", after=2)


def add_activity_heading(doc, number, cn, en, si=None):
    p = doc.add_paragraph()
    style_paragraph(p, before=7, after=4, line=1.0, keep=True)
    font_run(p.add_run(f"{number}  {cn}"), 12, True, CORAL)
    font_run(p.add_run(f"  {en}"), 11.5, True, BLUE)
    if si:
        p.add_run("\n")
        font_run(p.add_run(si), 9.5, False, MUTED)
    return p


def add_answer_lines(doc, count=3, prefix=""):
    for i in range(count):
        p = doc.add_paragraph()
        style_paragraph(p, after=4, line=1.0)
        if prefix and i == 0:
            font_run(p.add_run(prefix + " "), 10, False, INK)
        font_run(p.add_run("________________________________________________________________________________"), 9, False, GRID)


def add_choice(doc, question, options):
    p = doc.add_paragraph()
    style_paragraph(p, after=2, line=1.0)
    font_run(p.add_run(question), 10.5, True, INK)
    p = doc.add_paragraph()
    style_paragraph(p, after=5, line=1.0)
    for index, option in enumerate(options, 1):
        font_run(p.add_run(f"  {index}) {option}   "), 10.2, False, INK)


def add_vocab_table(doc, vocab):
    table = doc.add_table(rows=1, cols=4)
    set_table_geometry(table, [1350, 1900, 3300, CONTENT_WIDTH_DXA - 6550])
    set_table_borders(table)
    headers = ["汉字", "Pinyin", "සිංහල", "English"]
    for i, value in enumerate(headers):
        cell = table.rows[0].cells[i]
        set_cell_shading(cell, NAVY)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        font_run(p.add_run(value), 9.5, True, WHITE)
    set_repeat_table_header(table.rows[0])
    for char, pinyin, si, en in vocab:
        cells = table.add_row().cells
        for i, value in enumerate((char, pinyin, si, en)):
            p = cells[i].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i < 2 else WD_ALIGN_PARAGRAPH.LEFT
            font_run(p.add_run(value), 10.5 if i == 0 else 8.6, i == 0, INK)
        if len(table.rows) % 2 == 1:
            for cell in cells:
                set_cell_shading(cell, LIGHT)
    add_para(doc, "", after=1)


def add_trace_grid(doc, entries):
    table = doc.add_table(rows=1, cols=8)
    widths = [CONTENT_WIDTH_DXA // 8] * 8
    widths[-1] += CONTENT_WIDTH_DXA - sum(widths)
    set_table_geometry(table, widths)
    set_table_borders(table, color=GRID)
    for char, strokes in entries:
        cells = table.add_row().cells
        values = [f"{char}\n{strokes}画", char, char, "", "", "", "", ""]
        for i, value in enumerate(values):
            p = cells[i].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            font_run(p.add_run(value), 17 if i else 10, i == 0, MUTED if i in (1, 2) else INK)
            cells[i].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            tr_pr = cells[i]._tc.getparent().get_or_add_trPr()
            height = OxmlElement("w:trHeight")
            height.set(qn("w:val"), "660")
            height.set(qn("w:hRule"), "atLeast")
            tr_pr.append(height)
    add_para(doc, "画数 = stroke count. Trace the pale examples, then write from memory.", 8.5, False, MUTED, italic=True, after=2)


def add_grammar_table(doc, grammar):
    table = doc.add_table(rows=1, cols=2)
    set_table_geometry(table, [3100, CONTENT_WIDTH_DXA - 3100])
    set_table_borders(table)
    for i, value in enumerate(["Pattern", "Use and example"]):
        set_cell_shading(table.rows[0].cells[i], NAVY)
        p = table.rows[0].cells[i].paragraphs[0]
        font_run(p.add_run(value), 9.5, True, WHITE)
    for pattern, explanation in grammar:
        cells = table.add_row().cells
        font_run(cells[0].paragraphs[0].add_run(pattern), 10.5, True, CORAL)
        font_run(cells[1].paragraphs[0].add_run(explanation), 9.3, False, INK)
    add_para(doc, "", after=1)


def add_reading_box(doc, text):
    table = doc.add_table(rows=1, cols=1)
    set_table_geometry(table, [CONTENT_WIDTH_DXA])
    set_table_borders(table, color=BLUE, size=9)
    set_cell_shading(table.cell(0, 0), SKY)
    p = table.cell(0, 0).paragraphs[0]
    for idx, line in enumerate(text.split("\n")):
        if idx:
            p.add_run("\n")
        font_run(p.add_run(line), 11, False, INK)
    add_para(doc, "", after=1)


def add_self_check(doc):
    table = doc.add_table(rows=1, cols=4)
    set_table_geometry(table, [CONTENT_WIDTH_DXA - 2700, 900, 900, 900])
    set_table_borders(table)
    for i, value in enumerate(["I can...", "Yes", "Almost", "Not yet"]):
        set_cell_shading(table.rows[0].cells[i], NAVY)
        p = table.rows[0].cells[i].paragraphs[0]
        font_run(p.add_run(value), 8.8, True, WHITE)
    for label in ["recognise the key words", "use the grammar patterns", "understand the reading", "speak without reading every word", "write a short response"]:
        cells = table.add_row().cells
        font_run(cells[0].paragraphs[0].add_run(label), 8.8, False, INK)
        for cell in cells[1:]:
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            font_run(p.add_run("□"), 12, False, INK)


def add_badge_strip(doc, labels):
    fills = [CORAL, BLUE, PURPLE, GREEN]
    table = doc.add_table(rows=1, cols=len(labels))
    widths = [CONTENT_WIDTH_DXA // len(labels)] * len(labels)
    widths[-1] += CONTENT_WIDTH_DXA - sum(widths)
    set_table_geometry(table, widths)
    set_table_borders(table, color=WHITE, size=5)
    for idx, label in enumerate(labels):
        cell = table.rows[0].cells[idx]
        set_cell_shading(cell, fills[idx % len(fills)])
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        font_run(p.add_run(label), 9.2, True, WHITE)
    add_para(doc, "", after=1)


def add_points_box(doc, label="MY SCORE"):
    table = doc.add_table(rows=1, cols=3)
    set_table_geometry(table, [2200, 3900, CONTENT_WIDTH_DXA - 6100])
    set_table_borders(table, color=GOLD, size=8)
    values = [(label, PALE_GOLD), ("Points: ____ / 20", WHITE), ("Teacher: __________", WHITE)]
    for idx, (value, fill) in enumerate(values):
        set_cell_shading(table.rows[0].cells[idx], fill)
        p = table.rows[0].cells[idx].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        font_run(p.add_run(value), 9.5, idx == 0, NAVY)


def add_fun_lab_page(doc, unit):
    note, missions = EXTENSION_NOTES[unit["no"]]
    add_page_break(doc)
    add_banner(doc, f"LESSON {unit['no']} | PLAY", "游戏口语站", "Vocabulary games and speaking missions")
    add_badge_strip(doc, ["LOOK", "REMEMBER", "SPEAK", "CREATE"])

    add_activity_heading(doc, "1", "九宫格挑战", "Nine-word challenge")
    add_para(doc, "Work in pairs. Point to a word, say its Pinyin and meaning, then use it in a phrase. Colour the box after a correct answer.", 9.4, False, MUTED)
    words = [item[0] for item in unit["vocab"][:9]]
    table = doc.add_table(rows=3, cols=3)
    set_table_geometry(table, [CONTENT_WIDTH_DXA // 3, CONTENT_WIDTH_DXA // 3, CONTENT_WIDTH_DXA - 2 * (CONTENT_WIDTH_DXA // 3)])
    set_table_borders(table, color=BLUE, size=8)
    for idx, word in enumerate(words):
        cell = table.cell(idx // 3, idx % 3)
        set_cell_shading(cell, SKY if idx % 2 == 0 else MINT)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        font_run(p.add_run(word), 17, True, NAVY)

    add_activity_heading(doc, "2", "口语任务卡", "Speaking mission cards")
    table = doc.add_table(rows=2, cols=2)
    set_table_geometry(table, [CONTENT_WIDTH_DXA // 2, CONTENT_WIDTH_DXA - CONTENT_WIDTH_DXA // 2])
    set_table_borders(table, color=PURPLE, size=8)
    for idx, mission in enumerate(missions):
        cell = table.cell(idx // 2, idx % 2)
        set_cell_shading(cell, "F2EEFA" if idx % 2 == 0 else WHITE)
        font_run(cell.paragraphs[0].add_run(f"MISSION {idx + 1}\n{mission}"), 10, True if idx < 2 else False, INK)

    add_activity_heading(doc, "3", "文化小贴士", "Culture and language note")
    table = doc.add_table(rows=1, cols=1)
    set_table_geometry(table, [CONTENT_WIDTH_DXA])
    set_table_borders(table, color=GOLD, size=8)
    set_cell_shading(table.cell(0, 0), PALE_GOLD)
    font_run(table.cell(0, 0).paragraphs[0].add_run(note), 10.2, False, INK)

    add_activity_heading(doc, "4", "我的新句子", "My best new sentence")
    add_answer_lines(doc, 2)
    add_points_box(doc, "TEAM POINTS")


def add_home_practice_page(doc, unit):
    add_page_break(doc)
    add_banner(doc, f"LESSON {unit['no']} | HOME", "家庭练习", "Independent practice and family check")
    add_badge_strip(doc, ["MATCH", "WRITE", "TRANSLATE", "REFLECT"])

    add_activity_heading(doc, "1", "连一连", "Match each word to its meaning")
    selected = unit["vocab"][:6]
    meanings = list(reversed([item[3] for item in selected]))
    table = doc.add_table(rows=7, cols=2)
    set_table_geometry(table, [CONTENT_WIDTH_DXA // 2, CONTENT_WIDTH_DXA - CONTENT_WIDTH_DXA // 2])
    set_table_borders(table)
    for idx, value in enumerate(["Chinese", "Meanings"]):
        set_cell_shading(table.rows[0].cells[idx], NAVY)
        font_run(table.rows[0].cells[idx].paragraphs[0].add_run(value), 9.2, True, WHITE)
    for idx in range(6):
        left = f"{idx + 1}. {selected[idx][0]}   Answer: ____"
        right = f"{chr(65 + idx)}. {meanings[idx]}"
        font_run(table.rows[idx + 1].cells[0].paragraphs[0].add_run(left), 9.5, True, INK)
        font_run(table.rows[idx + 1].cells[1].paragraphs[0].add_run(right), 9.2, False, INK)
        if idx % 2 == 1:
            set_cell_shading(table.rows[idx + 1].cells[0], LIGHT)
            set_cell_shading(table.rows[idx + 1].cells[1], LIGHT)

    add_activity_heading(doc, "2", "看拼音写汉字", "Write characters from memory")
    p = doc.add_paragraph()
    style_paragraph(p, after=5, line=1.0)
    for char, pinyin, _, _ in selected[:4]:
        font_run(p.add_run(f"{pinyin}: 田  田  田     "), 10.2, False, INK)

    add_activity_heading(doc, "3", "翻译阶梯", "Translation ladder")
    cn, si = unit["translation"][0]
    add_para(doc, f"Chinese -> Sinhala/English: {cn}", 10, True, INK, after=1)
    add_answer_lines(doc, 1)
    add_para(doc, f"Sinhala -> Chinese: {si}", 10, True, INK, after=1)
    add_answer_lines(doc, 1)

    add_activity_heading(doc, "4", "本周反思", "Weekly reflection")
    add_para(doc, "The easiest part was: __________________________    I will practise: __________________________", 9.5)
    add_para(doc, "Student signature: __________________    Parent/guardian: __________________    Date: __________", 9.2, False, MUTED)
    add_points_box(doc)


def add_essay_practice_page(doc, number, essay):
    add_page_break(doc)
    add_banner(doc, f"ESSAY {number}", essay["title"], essay["english"])
    add_badge_strip(doc, ["PLAN", "WORDS", "WRITE", "CHECK"])
    add_para(doc, "Write 60-80 Chinese characters. Use the planning questions and vocabulary bank before writing your final paragraph.", 9.5, False, MUTED)

    add_activity_heading(doc, "1", "想一想", "Plan your ideas")
    table = doc.add_table(rows=2, cols=2)
    set_table_geometry(table, [CONTENT_WIDTH_DXA // 2, CONTENT_WIDTH_DXA - CONTENT_WIDTH_DXA // 2])
    set_table_borders(table, color=BLUE, size=7)
    for idx, prompt in enumerate(essay["prompts"]):
        cell = table.cell(idx // 2, idx % 2)
        set_cell_shading(cell, SKY if idx % 2 == 0 else MINT)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        p = cell.paragraphs[0]
        font_run(p.add_run(prompt + "\n________________________________"), 9.4, True, INK)

    add_activity_heading(doc, "2", "词语银行", "Useful word bank")
    table = doc.add_table(rows=1, cols=1)
    set_table_geometry(table, [CONTENT_WIDTH_DXA])
    set_table_borders(table, color=GOLD, size=8)
    set_cell_shading(table.cell(0, 0), PALE_GOLD)
    p = table.cell(0, 0).paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    font_run(p.add_run(essay["words"]), 10.2, True, NAVY)

    add_activity_heading(doc, "3", "开头句", "Sentence starters")
    add_para(doc, "   |   ".join(essay["starters"]), 10.2, True, PURPLE, align=WD_ALIGN_PARAGRAPH.CENTER)

    add_activity_heading(doc, "4", "写一写", "Write your paragraph")
    add_answer_lines(doc, 10)

    add_para(doc, "□ 60-80 characters   □ Complete sentences   □ Correct punctuation   □ Checked key characters", 9.2, True, GREEN, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_points_box(doc, "ESSAY SCORE")


def add_translation_practice_page(doc, number, activity):
    add_page_break(doc)
    add_banner(doc, f"TRANSLATION {number}", "短文翻译", "Passage translation - 20 marks")
    add_badge_strip(doc, ["READ", "MARK", "TRANSLATE", "CHECK"])
    add_para(doc, f"Translate the passage into {activity['languages']}. Choose one target language and write a complete, natural translation.", 9.7, True, NAVY)

    add_activity_heading(doc, "1", "阅读短文", "Read the Chinese passage")
    add_reading_box(doc, activity["chinese"])
    add_activity_heading(doc, "2", "翻译", "Write your translation")
    add_para(doc, "Language chosen: ____________________", 9.5, True, PURPLE)
    add_answer_lines(doc, 12)
    add_para(doc, "□ All ideas included   □ Names and numbers checked   □ Natural sentences   □ Final spelling check", 9.1, True, GREEN, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_points_box(doc, "TRANSLATION SCORE")


def add_translation_model_page(doc, number, activity):
    add_page_break(doc)
    add_banner(doc, f"TRANS KEY {number}", "翻译参考", "Sinhala and English model translations")
    add_para(doc, "A good translation may use different wording while preserving every important idea, name, number and relationship.", 9.2, False, MUTED)

    add_activity_heading(doc, "A", "僧伽罗语", "Sinhala model translation")
    table = doc.add_table(rows=1, cols=1)
    set_table_geometry(table, [CONTENT_WIDTH_DXA])
    set_table_borders(table, color=GREEN, size=7)
    set_cell_shading(table.cell(0, 0), MINT)
    font_run(table.cell(0, 0).paragraphs[0].add_run(activity["sinhala"]), 9.1, False, INK)

    add_activity_heading(doc, "B", "英语", "English model translation")
    table = doc.add_table(rows=1, cols=1)
    set_table_geometry(table, [CONTENT_WIDTH_DXA])
    set_table_borders(table, color=BLUE, size=7)
    set_cell_shading(table.cell(0, 0), SKY)
    font_run(table.cell(0, 0).paragraphs[0].add_run(activity["english"]), 9.1, False, INK)

    add_activity_heading(doc, "C", "评分提示", "20-mark checking guide")
    add_para(doc, "Meaning /10 ____   Completeness /4 ____   Natural language /4 ____   Spelling and punctuation /2 ____", 9.3, True, PURPLE)


def build_document():
    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Inches(0.65)
    section.bottom_margin = Inches(0.65)
    section.left_margin = Inches(0.65)
    section.right_margin = Inches(0.65)
    section.header_distance = Inches(0.32)
    section.footer_distance = Inches(0.32)
    section.different_first_page_header_footer = True

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = RGBColor.from_string(INK)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")
    normal._element.rPr.rFonts.set(qn("w:cs"), "Nirmala UI")
    normal.paragraph_format.space_after = Pt(4)
    normal.paragraph_format.line_spacing = 1.08
    for style_name, size, color, before, after in [
        ("Title", 28, NAVY, 0, 6), ("Subtitle", 13, MUTED, 0, 8),
        ("Heading 1", 18, CORAL, 14, 8), ("Heading 2", 14, BLUE, 10, 6),
        ("Heading 3", 11.5, NAVY, 8, 4),
    ]:
        style = styles[style_name]
        style.font.name = "Arial"
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor.from_string(color)
        style.font.bold = style_name != "Subtitle"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")
        style._element.rPr.rFonts.set(qn("w:cs"), "Nirmala UI")
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True

    header = section.header
    p = header.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    font_run(p.add_run("汉语动起来! | Grade 10 Chinese Expanded Student Workbook"), 8.5, True, NAVY)
    footer = section.footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    font_run(p.add_run("Grade 10 Chinese | "), 8.2, False, MUTED)
    add_page_field(p)

    # Cover
    add_para(doc, "GRADE 10 | EXPANDED STUDENT EDITION", 10.5, True, CORAL, before=4, after=3, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_para(doc, "汉语动起来！", 31, True, NAVY, after=2, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_para(doc, "චීන භාෂාව ක්‍රියාවෙන්", 22, True, CORAL, after=3, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_para(doc, "Complete Chinese Activity Workbook - Translation & Essay Edition", 15, True, BLUE, after=4, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_badge_strip(doc, ["LEARN", "PLAY", "PRACTISE", "PROGRESS"])
    if COVER_IMAGE.exists():
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cover_picture = p.add_run().add_picture(str(COVER_IMAGE), width=Inches(6.7))
        cover_picture._inline.docPr.set(
            "descr",
            "Four Sri Lankan Grade 10 students learning Chinese together with books, speech bubbles and cultural study symbols.",
        )
    table = doc.add_table(rows=3, cols=2)
    set_table_geometry(table, [2500, CONTENT_WIDTH_DXA - 2500])
    set_table_borders(table, color=GRID)
    for r, (label, value) in enumerate([("Student name", ""), ("School", ""), ("Prepared by", "")]):
        set_cell_shading(table.rows[r].cells[0], PALE_GOLD)
        font_run(table.rows[r].cells[0].paragraphs[0].add_run(label), 9.5, True, NAVY)
        font_run(table.rows[r].cells[1].paragraphs[0].add_run(value + "________________________________"), 9.5, False, MUTED)

    add_page_break(doc)
    add_banner(doc, "START", "මෙම වැඩපොත භාවිත කරන ආකාරය", "How to use this workbook")
    add_para(doc, "මෙය ශ්‍රී ලංකා 10 ශ්‍රේණියේ චීන භාෂා විෂය සඳහා, පාඩම් 1-8 සහ වාර තුනේ හැකියා ආවරණය කරන මුල් ක්‍රියාකාරකම් වැඩපොතකි. මෙය නිල අධ්‍යාපන අමාත්‍යාංශ ප්‍රකාශනයක් නොවේ.", 10.5, False, INK, after=8)
    add_activity_heading(doc, "1", "先看目标。", "Read the learning targets.", "පාඩම ආරම්භයේ ඉලක්ක කියවන්න.")
    add_para(doc, "Each unit moves through SEE - SAY - TRACE - BUILD - READ - LISTEN - TALK - WRITE.", 11, True, NAVY)
    add_activity_heading(doc, "2", "先说，再写。", "Speak before you write.", "ලියන්නට පෙර යුගල වශයෙන් කතා කරන්න.")
    add_para(doc, "Teacher or partner reads the listening script from the answer section. Students should not see the script during the first listening.")
    add_activity_heading(doc, "3", "自己检查。", "Use the self-check.", "සෑම පාඩමක් අවසානයේ ස්වයං ඇගයීම සලකුණු කරන්න.")
    add_para(doc, "Suggested rhythm: vocabulary and pronunciation -> character writing -> grammar -> reading/listening -> communication -> exam practice.")
    add_activity_heading(doc, "4", "我的目标", "My goal")
    add_answer_lines(doc, 5)

    add_page_break(doc)
    add_banner(doc, "PASSPORT", "我的汉语学习护照", "My Chinese learning passport")
    add_badge_strip(doc, ["NAME", "GOAL", "EFFORT", "SUCCESS"])
    add_activity_heading(doc, "1", "我的中文名字", "My Chinese identity")
    passport_fields = [
        "My Chinese name: __________________________________________",
        "The meaning or reason for my name: ___________________________",
        "My favourite Chinese word: __________________________________",
        "My Grade 10 goal: ___________________________________________",
    ]
    for field in passport_fields:
        add_para(doc, field, 10.5, False, INK, after=7)
    add_activity_heading(doc, "2", "我的学习约定", "My learning promise")
    for promise in ["I will speak Chinese even when I am not completely sure.", "I will practise characters a little at a time.", "I will correct my mistakes and try again.", "I will help my partner learn."]:
        add_para(doc, "□ " + promise, 10.2)
    add_activity_heading(doc, "3", "我的奖励", "My reward after completing the book")
    add_answer_lines(doc, 3)
    add_para(doc, "Student signature: ____________________________     Date: ______________", 9.5, False, MUTED)

    add_page_break(doc)
    add_banner(doc, "PLANNER", "学习进度计划", "Eight-lesson study and assessment planner")
    add_para(doc, "Use one row after each lesson. Record the score, one word you can use confidently and the next practice target.", 9.5, False, MUTED)
    table = doc.add_table(rows=9, cols=5)
    set_table_geometry(table, [1100, 1800, 1400, 3500, CONTENT_WIDTH_DXA - 7800])
    set_table_borders(table)
    headers = ["Lesson", "Date", "Score /20", "A word I can use", "Next target"]
    for idx, header_text in enumerate(headers):
        set_cell_shading(table.rows[0].cells[idx], NAVY)
        font_run(table.rows[0].cells[idx].paragraphs[0].add_run(header_text), 8.5, True, WHITE)
    set_repeat_table_header(table.rows[0])
    for row_idx in range(1, 9):
        values = [str(row_idx), "", "", "", ""]
        for col_idx, value in enumerate(values):
            p = table.rows[row_idx].cells[col_idx].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if col_idx < 3 else WD_ALIGN_PARAGRAPH.LEFT
            font_run(p.add_run(value), 9.2, col_idx == 0, INK)
            if row_idx % 2 == 0:
                set_cell_shading(table.rows[row_idx].cells[col_idx], LIGHT)
    add_activity_heading(doc, "★", "奖励星", "Achievement stars")
    add_para(doc, "Vocab ★ ____   Characters ★ ____   Speaking ★ ____   Reading ★ ____   Writing ★ ____", 10.5, True, PURPLE, align=WD_ALIGN_PARAGRAPH.CENTER)

    add_page_break(doc)
    add_banner(doc, "MAP", "Syllabus coverage", "All-term competency map")
    coverage = [
        ("1.0 Characters and phonetics", "Pinyin initials/finals, four tones + neutral tone, stroke principles, basic characters", "Foundation + every unit"),
        ("2.0 Listening, reading and response", "Pronunciation discrimination, short recorded-style texts, reading comprehension, summarising", "Every unit + reviews"),
        ("3.0 Communication", "Situational dialogues, pair/group exchanges, short individual speech", "Talk Lab in every unit"),
        ("4.0 Grammar and structure", "Statements, questions, lexical items, measure words, numbers, currency, time/date", "Units 1-8 + mock test"),
    ]
    table = doc.add_table(rows=1, cols=3)
    set_table_geometry(table, [2500, 5000, CONTENT_WIDTH_DXA - 7500])
    set_table_borders(table)
    for i, h in enumerate(["Competency", "Workbook coverage", "Where"]):
        set_cell_shading(table.rows[0].cells[i], NAVY)
        font_run(table.rows[0].cells[i].paragraphs[0].add_run(h), 9, True, WHITE)
    for row in coverage:
        cells = table.add_row().cells
        for i, value in enumerate(row):
            font_run(cells[i].paragraphs[0].add_run(value), 8.8, i == 0, INK)
    add_activity_heading(doc, "✓", "වාර ආවරණය", "Term coverage")
    for text in ["Term 1: sounds, tones, strokes, greetings, identity and reading foundations.", "Term 2: communication, family, objects, measure words, numbers, shopping and currency.", "Term 3: speaking, plans, time/date, travel, locations and integrated writing."]:
        add_para(doc, "□ " + text, 10.2, False, INK)
    add_activity_heading(doc, "✓", "විභාග හැකියා", "Exam skills")
    add_para(doc, "Pinyin and tones | character recognition | stroke count | antonyms | measure words | particles/adverbs | word order | translation | reading | essay/dialogue writing")

    add_page_break(doc)
    add_banner(doc, "CONTENTS", "පාඩම් අන්තර්ගතය", "Contents")
    rows = [("Foundation", "Pinyin, tones and stroke order", "Start here")]
    for u in UNITS:
        rows.append((f"Lesson {u['no']}", u["title"], u["theme"]))
    rows += [("Play + Home", "Two extension pages in every lesson", "Games, speaking and independent practice"), ("Reviews", "Term 1, Term 2 and Term 3 review", "After Lessons 2, 5 and 8"), ("Toolkit", "Measure words, grammar repair and writing", "Whole-syllabus revision"), ("Translation", "10 passage-translation activities", "Chinese to Sinhala, Tamil or English"), ("Essays", "10 guided composition topics", "Planning, vocabulary, writing and self-check"), ("Mock", "Final integrated test", "All competencies"), ("Answers", "Answer key + model translations", "Teacher/independent study")]
    table = doc.add_table(rows=1, cols=3)
    set_table_geometry(table, [1700, 2800, CONTENT_WIDTH_DXA - 4500])
    set_table_borders(table)
    for i, h in enumerate(["Section", "Chinese", "Focus"]):
        set_cell_shading(table.rows[0].cells[i], NAVY)
        font_run(table.rows[0].cells[i].paragraphs[0].add_run(h), 9.2, True, WHITE)
    for row in rows:
        cells = table.add_row().cells
        for i, value in enumerate(row):
            font_run(cells[i].paragraphs[0].add_run(value), 9.2, i == 0, INK)
    add_activity_heading(doc, "★", "My progress tracker", "Colour one circle after each lesson")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    font_run(p.add_run("1  ○    2  ○    3  ○    4  ○    5  ○    6  ○    7  ○    8  ○"), 16, True, CORAL)

    # Foundation pages
    add_page_break(doc)
    add_banner(doc, "FOUNDATION A", "拼音 Pinyin", "Initials, finals and syllable building")
    add_activity_heading(doc, "1", "声母和韵母", "Initials and finals")
    initials = "b p m f | d t n l | g k h | j q x | zh ch sh r | z c s"
    finals = "a o e i u ü | ai ei ao ou | an en ang eng ong | ia ie iao iu | ua uo uai ui | üe ün"
    add_reading_box(doc, f"Initials: {initials}\nFinals: {finals}")
    add_para(doc, "Build and read aloud: m + a = ma | h + ao = hao | x + ue = xue | zh + ong = zhong", 11, True, NAVY)
    add_activity_heading(doc, "2", "拼一拼", "Build syllables")
    for prompt in ["n + i = ______", "l + ü = ______", "sh + eng = ______", "j + ia = ______", "q + ing = ______", "g + uo = ______"]:
        add_para(doc, prompt, 11, False, INK)
    add_activity_heading(doc, "3", "读一读", "Read in pairs")
    add_para(doc, "ma - mai - man - mang | shi - shui - sheng | jia - jie - jiao | xue - xiao - xiong", 12, False, INK)
    add_answer_lines(doc, 4, "Teacher/partner notes:")

    add_page_break(doc)
    add_banner(doc, "FOUNDATION B", "声调 Tones", "Four tones and the neutral tone")
    add_activity_heading(doc, "1", "跟着声调读", "Read the tone ladder")
    add_reading_box(doc, "1st: mā  high and level     2nd: má  rising     3rd: mǎ  dip/rise     4th: mà  falling     neutral: ma  light")
    add_activity_heading(doc, "2", "辨一辨", "Circle the syllable the teacher reads")
    for line in ["mā   má   mǎ   mà", "shī   shí   shǐ   shì", "tā   tá   tǎ   tà", "yī   yí   yǐ   yì"]:
        add_para(doc, "○ " + line, 13, False, INK)
    add_activity_heading(doc, "3", "规则", "Tone-mark rules")
    add_para(doc, "Mark a first; if there is no a, mark o or e. In iu and ui, mark the final vowel: liú, guì. Write ü after n/l, but omit the dots after j/q/x: nǚ, lǜ, xué.")
    add_activity_heading(doc, "4", "写声调", "Add the correct tone mark")
    for prompt in ["ni hao -> __________", "xue sheng -> __________", "lao shi -> __________", "Zhong guo -> __________", "peng you -> __________"]:
        add_para(doc, prompt, 11)

    add_page_break(doc)
    add_banner(doc, "FOUNDATION C", "笔画和笔顺", "Basic strokes and stroke order")
    add_activity_heading(doc, "1", "基本笔画", "Basic strokes")
    add_reading_box(doc, "横 héng  一    竖 shù  丨    撇 piě  丿    捺 nà  ㇏    点 diǎn  丶    提 tí  ㇀    折 zhé  𠃍    钩 gōu  亅")
    add_activity_heading(doc, "2", "笔顺规则", "Core order rules")
    rules = ["top before bottom", "left before right", "horizontal before vertical", "outside before inside", "close the frame last", "centre before symmetrical sides"]
    for i, rule in enumerate(rules, 1):
        add_para(doc, f"{i}. {rule}", 10.5)
    add_activity_heading(doc, "3", "描一描，写一写", "Trace and write")
    add_trace_grid(doc, [("一", 1), ("十", 2), ("人", 2), ("口", 3), ("中", 4), ("国", 8)])

    add_page_break(doc)
    add_banner(doc, "FOUNDATION D", "听 - 说 - 读 - 写", "Four-skill warm-up")
    add_activity_heading(doc, "1", "听一听", "Listen and tick")
    for q in ["1. mā / mǎ", "2. shí / shì", "3. xué / xuě", "4. mǎi / mài"]:
        add_para(doc, "□ " + q, 11)
    add_activity_heading(doc, "2", "说一说", "Tone-pair relay")
    add_para(doc, "In pairs, Student A reads one syllable; Student B points to the tone number and repeats it. Swap after five turns.")
    add_activity_heading(doc, "3", "读一读", "Read the mini text")
    add_reading_box(doc, "你好！我叫安妮。我是学生。我学习汉语。")
    add_para(doc, "Underline the words you already recognise. Circle the sentence pattern used to introduce a name.")
    add_activity_heading(doc, "4", "写一写", "Copy with correct spacing")
    add_trace_grid(doc, [("你", 7), ("好", 6), ("我", 7), ("是", 9), ("学", 8), ("生", 5)])

    # Unit pages
    for unit in UNITS:
        add_page_break(doc)
        add_banner(doc, f"LESSON {unit['no']}", unit["title"], unit["si"])
        add_para(doc, unit["theme"], 12, True, BLUE, after=6)
        add_activity_heading(doc, "GOALS", "学习目标", "Learning targets")
        for goal in ["recognise and pronounce the key vocabulary", "write six focus characters", "use the unit grammar in short sentences", "understand a short reading and listening text", "complete a real-life pair task"]:
            add_para(doc, "□ " + goal, 9.5, False, INK, after=2)
        add_activity_heading(doc, "1", "词语银行", "Vocabulary bank", "වචන බැංකුව")
        add_vocab_table(doc, unit["vocab"])

        add_page_break(doc)
        add_banner(doc, f"LESSON {unit['no']} | SOUND", "听音辨调", "Pinyin, tones and characters")
        add_activity_heading(doc, "1", "选择正确拼音和声调", "Choose the correct Pinyin and tones")
        for idx, (char, options, _) in enumerate(unit["tone"], 1):
            add_choice(doc, f"{idx}. {char}", options)
        add_activity_heading(doc, "2", "描一描，写一写", "Trace and write the characters")
        add_trace_grid(doc, unit["trace"])
        add_activity_heading(doc, "3", "数笔画", "Write the stroke count")
        p = doc.add_paragraph()
        for char, _ in unit["trace"]:
            font_run(p.add_run(f"{char}: ____ 画     "), 11, False, INK)
        add_activity_heading(doc, "4", "听写", "Dictation")
        add_para(doc, "Teacher chooses five items from the vocabulary bank. Write Pinyin first, then characters.", 9.5, False, MUTED)
        add_answer_lines(doc, 5)

        add_page_break(doc)
        add_banner(doc, f"LESSON {unit['no']} | BUILD", "句子工场", "Grammar and sentence building")
        add_grammar_table(doc, unit["grammar"])
        add_activity_heading(doc, "1", "填空", "Fill in the blanks")
        for idx, (prompt, _) in enumerate(unit["fill"], 1):
            add_para(doc, f"{idx}. {prompt}", 10.8)
        add_activity_heading(doc, "2", "排列词语", "Put the words in the correct order")
        for idx, (scrambled, _) in enumerate(unit["reorder"], 1):
            add_para(doc, f"{idx}. {scrambled}", 10.5, True, INK, after=1)
            add_answer_lines(doc, 1)
        add_activity_heading(doc, "3", "自己造句", "Make two original sentences")
        add_answer_lines(doc, 3)

        add_page_break(doc)
        add_banner(doc, f"LESSON {unit['no']} | INPUT", "读一读，听一听", "Reading and listening")
        add_activity_heading(doc, "1", "阅读", "Read the text twice")
        add_reading_box(doc, unit["reading"])
        for idx, (question, _) in enumerate(unit["rq"], 1):
            add_para(doc, f"{idx}. {question}", 10.5, True, INK, after=1)
            add_answer_lines(doc, 1)
        add_activity_heading(doc, "2", "听力", "Listen twice - do not look at the script")
        add_para(doc, "First listening: write two words you hear. Second listening: choose the answers.", 9.3, False, MUTED)
        add_answer_lines(doc, 1)
        for idx, (question, options, _) in enumerate(unit["lq"], 1):
            add_choice(doc, f"{idx}. {question}", options)
        add_activity_heading(doc, "3", "一句话总结", "Summarise in one Chinese sentence")
        add_answer_lines(doc, 2)

        add_page_break(doc)
        add_banner(doc, f"LESSON {unit['no']} | OUTPUT", "说一说，考一考", "Communication and exam practice")
        add_activity_heading(doc, "1", "对话", "Complete and perform the dialogue")
        table = doc.add_table(rows=1, cols=1)
        set_table_geometry(table, [CONTENT_WIDTH_DXA])
        set_table_borders(table, color=GOLD, size=9)
        set_cell_shading(table.cell(0, 0), PALE_GOLD)
        p = table.cell(0, 0).paragraphs[0]
        for idx, line in enumerate(unit["dialogue"]):
            if idx:
                p.add_run("\n")
            font_run(p.add_run(line), 10.5, False, INK)
        add_activity_heading(doc, "2", "任务", "Pair/group task")
        add_para(doc, unit["task"], 10.2)
        add_activity_heading(doc, "3", "考试练习", "Mini exam")
        for idx, (question, options, _) in enumerate(unit["exam"], 1):
            add_choice(doc, f"{idx}. {question}", options)
        for idx, (cn, _) in enumerate(unit["translation"], 1):
            add_para(doc, f"Translate {idx}: {cn}", 10.2, True, INK, after=1)
            add_answer_lines(doc, 1)
        add_para(doc, "Writing: " + unit["writing"], 9.8, True, BLUE)
        add_answer_lines(doc, 4)
        add_activity_heading(doc, "4", "自我检查", "Self-check")
        add_self_check(doc)

        add_fun_lab_page(doc, unit)
        add_home_practice_page(doc, unit)

        if unit["no"] in (2, 5, 8):
            term = {2: 1, 5: 2, 8: 3}[unit["no"]]
            add_page_break(doc)
            add_banner(doc, f"TERM {term}", f"第{term}学期复习", f"Term {term} integrated review")
            add_activity_heading(doc, "A", "语音和汉字", "Pinyin and characters")
            review_units = UNITS[0:2] if term == 1 else (UNITS[2:5] if term == 2 else UNITS[5:8])
            for i, ru in enumerate(review_units, 1):
                char, opts, ans = ru["tone"][0]
                add_choice(doc, f"{i}. {char}", opts)
            add_activity_heading(doc, "B", "语法", "Grammar")
            for i, ru in enumerate(review_units, 1):
                q, opts, ans = ru["exam"][0]
                add_choice(doc, f"{i}. {q}", opts)
            add_activity_heading(doc, "C", "阅读和写作", "Reading and writing")
            combined = " ".join(ru["reading"].replace("\n", " ") for ru in review_units[:2])
            add_reading_box(doc, combined)
            add_para(doc, "1. Write three facts from the text in English or Sinhala.", 10, True, INK)
            add_answer_lines(doc, 3)
            add_para(doc, "2. Write 50 Chinese characters using at least four grammar patterns from this term.", 10, True, INK)
            add_answer_lines(doc, 6)

    # Whole-syllabus revision toolkit
    add_page_break(doc)
    add_banner(doc, "TOOLKIT 1", "量词运动会", "Measure-word stadium")
    add_badge_strip(doc, ["READ", "CHOOSE", "CHECK", "SCORE"])
    add_para(doc, "Word bank: 个  口  本  张  件  条  家", 12, True, NAVY, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_activity_heading(doc, "A", "选择量词", "Choose the correct measure word")
    for idx, (prompt, _) in enumerate(REVISION_MEASURE_ITEMS, 1):
        add_para(doc, f"{idx}. {prompt}", 10.8)
    add_activity_heading(doc, "B", "数字快跑", "Number and price sprint")
    for prompt in ["145 = ____________________", "2,300 = ____________________", "20,000 = ____________________", "六十元 + 二十元 = __________元", "九点半 = __________ (digital time)"]:
        add_para(doc, prompt, 10.5)
    add_activity_heading(doc, "C", "自己出题", "Create a classifier quiz")
    add_para(doc, "Write three new noun phrases. Give your quiz to a partner.", 9.5, False, MUTED)
    add_answer_lines(doc, 4)
    add_points_box(doc, "TOOLKIT SCORE")

    add_page_break(doc)
    add_banner(doc, "TOOLKIT 2", "语法急救站", "Grammar rescue station")
    add_badge_strip(doc, ["FIND", "FIX", "EXPLAIN", "RETRY"])
    add_para(doc, "Each sentence has one important Grade 10 grammar mistake. Rewrite it correctly and explain the rule to a partner.", 9.5, False, MUTED)
    for idx, (wrong, _) in enumerate(REVISION_REPAIR_ITEMS, 1):
        add_para(doc, f"{idx}. {wrong}", 10.5, True, INK, after=1)
        add_answer_lines(doc, 1)
    add_activity_heading(doc, "★", "规则卡", "My three rule cards")
    add_answer_lines(doc, 4)

    add_page_break(doc)
    add_banner(doc, "TOOLKIT 3", "写作搭建器", "60-80 character writing builder")
    add_badge_strip(doc, ["PLAN", "DRAFT", "CHECK", "IMPROVE"])
    add_activity_heading(doc, "1", "选择题目", "Choose a topic")
    add_para(doc, "□ 我和我的家    □ 我的星期六    □ 买衣服    □ 我的旅行计划    □ 从学校到银行", 10.5, True, NAVY)
    add_activity_heading(doc, "2", "五问计划", "Five-question plan")
    planner = [("Who? 谁？", ""), ("Where? 哪儿？", ""), ("When? 什么时候？", ""), ("What? 做什么？", ""), ("Extra detail", "")]
    table = doc.add_table(rows=5, cols=2)
    set_table_geometry(table, [2600, CONTENT_WIDTH_DXA - 2600])
    set_table_borders(table, color=BLUE, size=7)
    for idx, (label, _) in enumerate(planner):
        set_cell_shading(table.rows[idx].cells[0], SKY)
        font_run(table.rows[idx].cells[0].paragraphs[0].add_run(label), 9.5, True, NAVY)
        font_run(table.rows[idx].cells[1].paragraphs[0].add_run("________________________________________________"), 9, False, GRID)
    add_activity_heading(doc, "3", "自检", "Writer's checklist")
    for check in ["I used at least five complete sentences.", "I checked measure words and particles.", "I used time/date or place details.", "I checked characters and punctuation.", "I improved one sentence after feedback."]:
        add_para(doc, "□ " + check, 9.5, False, INK, after=2)
    add_activity_heading(doc, "4", "老师评分", "Teacher rubric - 20 marks")
    add_para(doc, "Content /5 ____   Grammar /5 ____   Vocabulary /4 ____   Characters /4 ____   Presentation /2 ____", 9.8, True, PURPLE)

    # Passage-translation practice bank
    for number, activity in enumerate(TRANSLATION_ACTIVITIES, 1):
        add_translation_practice_page(doc, number, activity)

    # Guided essay practice bank
    for number, essay in enumerate(ESSAY_TOPICS, 1):
        add_essay_practice_page(doc, number, essay)

    # Final mock test
    add_page_break(doc)
    add_banner(doc, "FINAL MOCK", "综合测试", "Grade 10 comprehensive practice test")
    add_para(doc, "Suggested time: 90 minutes | Total: 100 marks", 11, True, CORAL, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_activity_heading(doc, "PART A", "选择题", "Multiple choice - 30 marks")
    mock_items = []
    for unit in UNITS:
        mock_items.append(unit["tone"][1])
        mock_items.append(unit["exam"][1])
    for idx, (q, opts, _) in enumerate(mock_items, 1):
        add_choice(doc, f"{idx}. {q}", opts)
    add_page_break(doc)
    add_banner(doc, "FINAL MOCK", "句子和翻译", "Sentences and translation - 30 marks")
    add_activity_heading(doc, "PART B", "排列词语", "Reorder the words")
    for idx, unit in enumerate(UNITS, 1):
        scrambled, _ = unit["reorder"][0]
        add_para(doc, f"{idx}. {scrambled}", 10.5, True, INK)
        add_answer_lines(doc, 1)
    add_activity_heading(doc, "PART C", "翻译", "Translate")
    for idx, unit in enumerate(UNITS[:6], 1):
        cn, _ = unit["translation"][0]
        add_para(doc, f"{idx}. {cn}", 10.2, True, INK)
        add_answer_lines(doc, 1)
    add_page_break(doc)
    add_banner(doc, "FINAL MOCK", "阅读", "Reading - 20 marks")
    final_reading = "我叫林美。我是斯里兰卡人，今年十五岁。我家有五口人。星期六我和姐姐去商店买衣服，然后下午三点看电影。商店在银行旁边，离学校不远。下个月我们打算坐飞机去中国旅行。"
    add_reading_box(doc, final_reading)
    final_questions = ["林美是哪国人？", "她今年多大？", "她家有几口人？", "星期六她和谁去商店？", "商店在哪儿？", "下个月她打算做什么？"]
    for idx, q in enumerate(final_questions, 1):
        add_para(doc, f"{idx}. {q}", 10.5, True, INK)
        add_answer_lines(doc, 1)
    add_page_break(doc)
    add_banner(doc, "FINAL MOCK", "写作", "Writing - 20 marks")
    add_para(doc, "Choose ONE topic and write 60-80 Chinese characters.", 11, True, NAVY)
    topic_table = doc.add_table(rows=5, cols=2)
    set_table_geometry(topic_table, [CONTENT_WIDTH_DXA // 2, CONTENT_WIDTH_DXA - CONTENT_WIDTH_DXA // 2])
    set_table_borders(topic_table, color=GRID, size=6)
    for idx, essay in enumerate(ESSAY_TOPICS):
        cell = topic_table.cell(idx % 5, idx // 5)
        font_run(cell.paragraphs[0].add_run(f"{idx + 1}. {essay['title']}"), 10.2, True, NAVY)
    add_para(doc, "Plan: Who? Where? When? What? How?", 10, True, BLUE)
    add_answer_lines(doc, 13)

    # Answer key
    add_page_break(doc)
    add_banner(doc, "ANSWERS", "参考答案", "Answer key and model responses")
    add_para(doc, "Open speaking/writing tasks may have many correct answers. The models below show one acceptable form.", 9.5, False, MUTED)
    for unit in UNITS:
        add_page_break(doc)
        add_banner(doc, f"KEY {unit['no']}", unit["title"], "Closed answers and models")
        tone_answers = "; ".join(f"{i}. {opts[ans-1]}" for i, (_, opts, ans) in enumerate(unit["tone"], 1))
        stroke_answers = "; ".join(f"{char} {strokes}" for char, strokes in unit["trace"])
        fill_answers = "; ".join(f"{i}. {ans}" for i, (_, ans) in enumerate(unit["fill"], 1))
        reorder_answers = "\n".join(f"{i}. {ans}" for i, (_, ans) in enumerate(unit["reorder"], 1))
        reading_answers = "\n".join(f"{i}. {ans}" for i, (_, ans) in enumerate(unit["rq"], 1))
        listening_answers = "; ".join(f"{i}. {opts[ans-1]}" for i, (_, opts, ans) in enumerate(unit["lq"], 1))
        exam_answers = "; ".join(f"{i}. {opts[ans-1]}" for i, (_, opts, ans) in enumerate(unit["exam"], 1))
        add_activity_heading(doc, "A", "语音和汉字", "Sound and characters")
        add_para(doc, "Pinyin: " + tone_answers)
        add_para(doc, "Stroke counts: " + stroke_answers)
        add_activity_heading(doc, "B", "语法", "Grammar")
        add_para(doc, "Fill: " + fill_answers)
        add_reading_box(doc, reorder_answers)
        add_activity_heading(doc, "C", "阅读", "Reading")
        add_reading_box(doc, reading_answers)
        add_activity_heading(doc, "D", "听力", "Listening script and answers")
        add_para(doc, unit["listen"], 10.5, False, INK)
        add_para(doc, "Answers: " + listening_answers, 10, True, BLUE)
        add_activity_heading(doc, "E", "考试练习", "Mini exam")
        add_para(doc, exam_answers)
        add_para(doc, "Translation models: " + " | ".join(f"{cn} = {si}" for cn, si in unit["translation"]), 9.5)
        home_match = "; ".join(f"{idx + 1}-{chr(65 + (5 - idx))}" for idx in range(6))
        add_activity_heading(doc, "F", "家庭练习", "Home-practice check")
        add_para(doc, "Matching: " + home_match, 9.5, True, PURPLE)
        add_para(doc, "Character-memory and translation items use the lesson vocabulary bank and the translation models above.", 8.8, False, MUTED)

    add_page_break(doc)
    add_banner(doc, "REVIEW KEY", "复习答案", "Term review answers")
    for term, review_units in [(1, UNITS[0:2]), (2, UNITS[2:5]), (3, UNITS[5:8])]:
        add_activity_heading(doc, str(term), f"第{term}学期", f"Term {term}")
        tone_ans = "; ".join(f"{i}. {ru['tone'][0][1][ru['tone'][0][2]-1]}" for i, ru in enumerate(review_units, 1))
        grammar_ans = "; ".join(f"{i}. {ru['exam'][0][1][ru['exam'][0][2]-1]}" for i, ru in enumerate(review_units, 1))
        add_para(doc, "A: " + tone_ans)
        add_para(doc, "B: " + grammar_ans)
        add_para(doc, "C: Accept any three accurate facts; writing must use four target patterns.", 9.5, False, MUTED)

    add_page_break(doc)
    add_banner(doc, "MOCK KEY", "综合测试答案", "Final mock answers")
    mock_answers = []
    for unit in UNITS:
        q = unit["tone"][1]
        mock_answers.append(q[1][q[2]-1])
        q = unit["exam"][1]
        mock_answers.append(q[1][q[2]-1])
    add_para(doc, "Part A: " + "; ".join(f"{i}. {a}" for i, a in enumerate(mock_answers, 1)), 9.5)
    add_activity_heading(doc, "B", "句子", "Sentence order")
    for idx, unit in enumerate(UNITS, 1):
        add_para(doc, f"{idx}. {unit['reorder'][0][1]}", 9.5)
    add_activity_heading(doc, "C", "翻译", "Translation")
    for idx, unit in enumerate(UNITS[:6], 1):
        add_para(doc, f"{idx}. {unit['translation'][0][1]}", 9.5)
    add_activity_heading(doc, "D", "阅读", "Reading")
    for idx, answer in enumerate(["她是斯里兰卡人。", "她十五岁。", "她家有五口人。", "她和姐姐去商店。", "在银行旁边。", "她打算坐飞机去中国旅行。"], 1):
        add_para(doc, f"{idx}. {answer}", 9.5)

    add_page_break(doc)
    add_banner(doc, "TOOLKIT KEY", "复习工具答案", "Whole-syllabus revision answers")
    add_activity_heading(doc, "1", "量词运动会", "Measure-word stadium")
    add_para(doc, "; ".join(f"{idx}. {answer}" for idx, (_, answer) in enumerate(REVISION_MEASURE_ITEMS, 1)), 10, True, NAVY)
    add_para(doc, "Numbers: 145 = 一百四十五; 2,300 = 两千三百; 20,000 = 两万; 六十元 + 二十元 = 八十元; 九点半 = 9:30.", 9.6)
    add_activity_heading(doc, "2", "语法急救站", "Grammar rescue station")
    for idx, (_, corrected) in enumerate(REVISION_REPAIR_ITEMS, 1):
        add_para(doc, f"{idx}. {corrected}", 9.6)
    add_activity_heading(doc, "3", "写作搭建器", "Writing builder")
    add_para(doc, "Answers vary. Use the 20-mark rubric: Content 5, Grammar 5, Vocabulary 4, Characters 4, Presentation 2.", 9.5, False, MUTED)

    for number, activity in enumerate(TRANSLATION_ACTIVITIES, 1):
        add_translation_model_page(doc, number, activity)

    add_page_break(doc)
    add_banner(doc, "WORD LIST", "总词表", "Alphabetical lesson index")
    all_vocab = []
    for unit in UNITS:
        for char, pinyin, si, en in unit["vocab"]:
            all_vocab.append((pinyin.lower(), char, pinyin, en, unit["no"]))
    all_vocab.sort()
    table = doc.add_table(rows=1, cols=4)
    set_table_geometry(table, [1700, 2500, CONTENT_WIDTH_DXA - 6000, 1800])
    set_table_borders(table)
    for i, h in enumerate(["汉字", "Pinyin", "English", "Lesson"]):
        set_cell_shading(table.rows[0].cells[i], NAVY)
        font_run(table.rows[0].cells[i].paragraphs[0].add_run(h), 9, True, WHITE)
    set_repeat_table_header(table.rows[0])
    for _, char, pinyin, en, unit_no in all_vocab:
        cells = table.add_row().cells
        for i, value in enumerate((char, pinyin, en, str(unit_no))):
            p = cells[i].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i in (0, 3) else WD_ALIGN_PARAGRAPH.LEFT
            font_run(p.add_run(value), 8.3, i == 0, INK)

    add_page_break(doc)
    add_banner(doc, "CERTIFICATE", "学习成就证书", "Grade 10 Chinese workbook completion")
    add_para(doc, "恭喜！ CONGRATULATIONS! සුබ පැතුම්!", 20, True, CORAL, before=28, after=18, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_para(doc, "This certificate is presented to", 12, False, MUTED, after=12, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_para(doc, "________________________________________________________", 15, True, NAVY, after=14, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_para(doc, "for completing the Grade 10 Chinese Expanded Student Workbook", 13, True, BLUE, after=6, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_para(doc, "and demonstrating progress in listening, speaking, reading, writing, vocabulary, grammar and character formation.", 10.5, False, INK, after=24, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_badge_strip(doc, ["听 LISTEN", "说 SPEAK", "读 READ", "写 WRITE"])
    add_para(doc, "", after=18)
    table = doc.add_table(rows=2, cols=3)
    set_table_geometry(table, [CONTENT_WIDTH_DXA // 3, CONTENT_WIDTH_DXA // 3, CONTENT_WIDTH_DXA - 2 * (CONTENT_WIDTH_DXA // 3)])
    set_table_borders(table, color=WHITE, size=0)
    for idx, value in enumerate(["____________________", "____________________", "____________________"]):
        p = table.rows[0].cells[idx].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        font_run(p.add_run(value), 10, False, GRID)
    for idx, value in enumerate(["Teacher", "School", "Date"]):
        p = table.rows[1].cells[idx].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        font_run(p.add_run(value), 9.5, True, NAVY)
    add_para(doc, "My next Chinese goal: ____________________________________________________________", 10, False, PURPLE, before=20, align=WD_ALIGN_PARAGRAPH.CENTER)

    # Document metadata
    doc.core_properties.title = "Grade 10 Chinese Complete Workbook - Translation and Essay Edition"
    doc.core_properties.subject = "Lessons 1-8, full syllabus coverage, translation passages, essay practice, games, home practice and revision toolkit"
    doc.core_properties.author = "Prepared for classroom use"
    doc.core_properties.keywords = "Grade 10, Chinese, Mandarin, Sinhala, workbook"
    doc.core_properties.comments = "Original activity workbook based on the supplied curriculum notes and assessment patterns."
    doc.save(OUTPUT_DOCX)
    print(OUTPUT_DOCX)


if __name__ == "__main__":
    build_document()
