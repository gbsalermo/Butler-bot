import re
import unicodedata

import companion_nlu_v2 as v2
import deterministic_memory as dm
from telegram_api import send_message


def _norm(text):
    value=unicodedata.normalize("NFKD",(text or "").lower())
    value="".join(ch for ch in value if not unicodedata.combining(ch))
    value=re.sub(r"[^a-z0-9 ]+"," ",value)
    return re.sub(r"\s+"," ",value).strip()

KNOWLEDGE = {
    "jake peralta": "Jake Peralta é o detetive protagonista de Brooklyn Nine-Nine: talentoso, infantil, competitivo e completamente incapaz de resistir a uma piada no meio do expediente. Em resumo, um ótimo policial com energia de aluno que descobriu que a sala tem projetor.",
    "palpatine": "Palpatine, também conhecido como Darth Sidious, é o grande manipulador político de Star Wars. Ele ascende dentro da República, transforma crise em poder e está no centro da queda de Anakin e da criação do Império. Um belo estudo de caso de por que ninguém devia dar poder emergencial sem data pra acabar.",
    "darth sidious": "Darth Sidious é a identidade Sith de Palpatine em Star Wars, responsável por arquitetar a queda da República e a ascensão do Império.",
    "platao": "Platão foi um filósofo grego da Antiguidade, aluno de Sócrates e mestre de Aristóteles. É associado à teoria das Formas, à Alegoria da Caverna e a diálogos como A República. Basicamente: o homem conseguiu transformar 'e se o que a gente vê não for a realidade inteira?' em uma carreira histórica.",
    "socrates": "Sócrates foi um filósofo ateniense conhecido principalmente pelos relatos de autores como Platão e Xenofonte. Seu método de perguntas e investigação crítica virou referência para o chamado método socrático.",
    "aristoteles": "Aristóteles foi filósofo grego, aluno de Platão, com influência enorme em lógica, ética, política, ciência e metafísica. É autor de obras como Ética a Nicômaco e Política.",
    "nietzsche": "Friedrich Nietzsche foi um filósofo alemão do século XIX que escreveu sobre moral, cultura, religião, criação de valores e niilismo. Entre suas obras estão Assim Falou Zaratustra e Além do Bem e do Mal.",
    "machado de assis": "Machado de Assis foi um dos maiores escritores brasileiros, fundador e primeiro presidente da Academia Brasileira de Letras. Memórias Póstumas de Brás Cubas e Dom Casmurro são duas das obras mais conhecidas.",
    "clarice lispector": "Clarice Lispector foi uma escritora brasileira conhecida por uma prosa introspectiva e psicológica. A Hora da Estrela e A Paixão Segundo G.H. estão entre suas obras mais conhecidas.",
    "george orwell": "George Orwell foi o escritor inglês de 1984 e A Revolução dos Bichos, obras fortemente associadas a autoritarismo, propaganda e manipulação política.",
    "stan lee": "Stan Lee foi escritor, editor e figura histórica da Marvel Comics, associado à criação ou cocriacão de personagens como Homem-Aranha, X-Men, Quarteto Fantástico e Hulk ao lado de artistas como Jack Kirby e Steve Ditko.",
    "hayao miyazaki": "Hayao Miyazaki é cineasta e animador japonês, cofundador do Studio Ghibli, ligado a filmes como A Viagem de Chihiro, Meu Amigo Totoro e Princesa Mononoke.",
    "studio ghibli": "Studio Ghibli é um estúdio japonês de animação conhecido por filmes como A Viagem de Chihiro, Meu Amigo Totoro, O Castelo Animado e Princesa Mononoke.",
    "breaking bad": "Breaking Bad é uma série de drama criminal sobre Walter White, um professor de química que entra no tráfico de metanfetamina e passa por uma transformação moral cada vez mais pesada.",
    "brooklyn nine nine": "Brooklyn Nine-Nine é uma sitcom policial ambientada numa delegacia fictícia do Brooklyn, com humor de equipe, amizade e trabalho. Jake Peralta e o capitão Holt são dois dos personagens centrais.",
    "bojack horseman": "BoJack Horseman é uma animação adulta que usa humor e absurdo para falar de fama, depressão, relações, autossabotagem e responsabilidade pessoal. É engraçada até decidir que hoje não será.",
    "bluey": "Bluey é uma animação australiana infantil sobre uma família de cães, mas com episódios que tratam de parentalidade, imaginação, frustração, perda e crescimento com uma eficiência ofensiva pra um desenho de sete minutos.",
    "star wars": "Star Wars é uma franquia de ficção científica e fantasia espacial criada por George Lucas, centrada em conflitos políticos, Jedi, Sith, a Força e diferentes gerações da família Skywalker.",
    "senhor dos aneis": "O Senhor dos Anéis é a obra de fantasia de J. R. R. Tolkien sobre a jornada para destruir o Um Anel e impedir o retorno de Sauron. É uma das obras mais influentes da fantasia moderna.",
    "one piece": "One Piece é um mangá e anime de Eiichiro Oda sobre Monkey D. Luffy e sua tripulação em busca do tesouro One Piece, misturando aventura, humor, política, amizade e construção de mundo em escala industrial.",
    "naruto": "Naruto é um mangá e anime criado por Masashi Kishimoto sobre Naruto Uzumaki, um jovem ninja que busca reconhecimento e sonha em se tornar Hokage.",
    "vincent van gogh": "Vincent van Gogh foi um pintor neerlandês pós-impressionista conhecido por obras como A Noite Estrelada e Girassóis, com forte uso de cor e pinceladas expressivas.",
    "picasso": "Pablo Picasso foi um artista espanhol central para a arte moderna e um dos nomes associados ao desenvolvimento do cubismo. Guernica é uma de suas obras mais conhecidas.",
    "beethoven": "Ludwig van Beethoven foi um compositor alemão do período de transição entre Classicismo e Romantismo, conhecido por suas sinfonias, sonatas e quartetos, incluindo a Nona Sinfonia.",
}

CULTURE_GUIDES = {
    "filmes": "Pra descobrir filme: IMDb e Letterboxd ajudam a explorar elenco, avaliações e listas. No YouTube, canais de análise de cinema e vídeo-ensaios costumam render mais que lista genérica de '10 filmes que mudaram minha vida'.",
    "series": "Pra séries: IMDb, JustWatch para descobrir onde algo está disponível e comunidades específicas da obra costumam ser mais úteis que ranking solto.",
    "livros": "Pra livros: Goodreads e Skoob são bons pontos de partida para catálogo e comunidade. Para literatura clássica, Domínio Público e Project Gutenberg podem ser úteis quando a obra está em domínio público.",
    "arte": "Pra arte: Google Arts & Culture, sites de museus como Louvre, MoMA e The Met e canais de história da arte no YouTube são um bom começo.",
    "filosofia": "Pra filosofia, Stanford Encyclopedia of Philosophy e Internet Encyclopedia of Philosophy são referências fortes para consulta. No YouTube, procure aulas universitárias ou canais que indiquem fontes.",
    "culinaria": "Pra culinária, prefiro fonte que mostre medida, técnica e resultado. TudoGostoso é útil para receita popular brasileira; Panelinha é boa referência prática. No YouTube, procure receitas que expliquem ponto, temperatura e substituições.",
    "programacao": "Pra programação, documentação oficial primeiro. MDN para web, documentação da linguagem/framework e depois Stack Overflow ou vídeos para complementar.",
    "youtube": "No YouTube eu usaria a busca como ferramenta: nome do assunto + 'aula', 'documentário', 'video essay', 'receita passo a passo' ou 'review'. Fonte e profundidade importam mais que número de inscritos.",
}


def _question_target(n):
    if not any(x in n for x in ("quem e ","o que e ","voce conhece ","fala sobre ","me explica ","me fale sobre ")): return None
    for key in sorted(KNOWLEDGE.keys(),key=len,reverse=True):
        if key in n:return key
    return None


# Evita que uma memória pessoal de primeiro nome (ex.: Jake, o gato) capture
# uma entidade cultural composta conhecida (ex.: Jake Peralta).
_original_find = dm._find_referenced

def _cultural_safe_find(entities,text):
    n=_norm(text)
    if any(key in n for key in KNOWLEDGE):
        return None
    return _original_find(entities,text)

dm._find_referenced = _cultural_safe_find


async def handle_message(db,token,message):
    chat_id=(message.get("chat") or {}).get("id")
    if chat_id is None:return False
    text=(message.get("text") or "").strip()
    if not text or text.startswith("/"):return False
    uid=await v2._uid(db,int(chat_id))
    if not uid:return False
    n=_norm(text)
    target=_question_target(n)
    if target:
        await send_message(token,int(chat_id),KNOWLEDGE[target]); return True
    if any(x in n for x in ("onde vejo","onde encontro","site pra","site para","onde pesquisar","onde pesquiso","me indica site","canal no youtube","youtube sobre")):
        for topic,answer in CULTURE_GUIDES.items():
            if topic in n or (topic=="filmes" and "filme" in n) or (topic=="series" and "serie" in n) or (topic=="culinaria" and any(x in n for x in ("cozinha","receita","culinaria"))):
                await send_message(token,int(chat_id),answer); return True
    return False
