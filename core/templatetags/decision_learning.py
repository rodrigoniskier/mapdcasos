"""Revisão teórica para os pontos de decisão da árvore bacteriana."""
from django import template

register = template.Library()

LEARNING_BASES = {1: 'Base de revisão: princípios de manejo de infecções de pele e stewardship na APS/SUS.',
 2: 'Base de revisão: princípios de manejo de infecções superficiais de pele e uso racional de antimicrobianos na '
    'APS/SUS.',
 3: 'Base de revisão: princípios de avaliação de pneumonia comunitária na APS e uso racional de antimicrobianos.',
 4: 'Base de revisão: princípios de manejo de ITU na APS, com diferenciação entre cistite, pielonefrite e IST.',
 5: 'Base de revisão: princípios de ITU complicada, sepse, cultura e controle de foco.',
 6: 'Base de revisão: princípios de avaliação de feridas, distinção entre colonização e infecção e stewardship.',
 7: 'Base de revisão: princípios de infecção intra-abdominal, anaeróbios, controle de foco e limites da APS.',
 8: 'Base de revisão: Ministério da Saúde — recomendações nacionais para diagnóstico, tratamento, vigilância e '
    'controle da tuberculose.',
 9: 'Base de revisão: microbiologia de Mycoplasma e princípios de manejo de pneumonia comunitária/atípica.',
 10: 'Base de revisão: Ministério da Saúde — PCDT para Atenção Integral às Pessoas com IST.'}

THEORY = {1: {'antibiotic': 'Antibiótico não deve ser automático em todo abscesso simples adequadamente drenado. A decisão depende de extensão, celulite associada, sinais sistêmicos, recorrência, comorbidades, imunossupressão e protocolos locais.',
     'culture': 'Cultura é mais útil quando o resultado pode mudar manejo: recorrência, falha terapêutica, quadro grave, epidemiologia incomum ou risco de resistência. Quando indicada, a amostra do material purulento é mais informativa que swab superficial de pele colonizada.',
     'etiology': 'Infecções cutâneas purulentas comunitárias são classicamente associadas a Staphylococcus aureus. Streptococcus pyogenes também causa infecções de pele, mas é mais lembrado em quadros não purulentos, como erisipela e celulite.',
     'followup': 'Safety-netting é parte do tratamento. Mesmo um paciente inicialmente estável precisa saber quais sinais indicam progressão: febre, expansão do eritema, dor desproporcional, nova coleção ou piora do estado geral.',
     'procedure': 'Quando existe coleção purulenta acessível, o princípio terapêutico central é controle de foco. Incisão e drenagem, quando indicadas e tecnicamente possíveis, removem o material infectado que o antibiótico isolado pode não resolver adequadamente.',
     'triage': 'Na APS, a primeira tarefa diante de uma lesão purulenta é definir se o problema é localizado ou se há sinais de infecção invasiva. Sinais vitais, extensão, localização, imunossupressão e presença de flutuação mudam o nível de cuidado e a necessidade de antibiótico ou encaminhamento.'},
 2: {'alarm': 'Febre, dor crescente e eritema em expansão sugerem que o processo pode ter ultrapassado a camada superficial, exigindo reavaliação para celulite, infecção profunda ou complicação sistêmica.',
     'etiology': 'Staphylococcus aureus e estreptococos beta-hemolíticos estão entre os agentes clássicos do impetigo. A participação relativa varia, portanto não é correto transformar um padrão clínico em certeza absoluta de espécie.',
     'prevention': 'Impetigo é transmissível por contato direto e por objetos contaminados. Higiene das mãos, cuidado das lesões, unhas curtas e não compartilhamento de toalhas/objetos reduzem disseminação.',
     'recognition': 'Impetigo é uma infecção bacteriana superficial da epiderme, comum na infância. Crostas melicéricas, lesões superficiais e ausência de toxemia favorecem esse diagnóstico, mas a consulta deve verificar extensão, bolhas, celulite e febre.',
     'testing': 'Impetigo típico e limitado costuma ser diagnóstico clínico. Cultura ganha valor em falha, recorrência, surtos, doença extensa ou situação em que conhecer o agente e a sensibilidade mudará o tratamento.',
     'treatment': 'A intensidade do tratamento deve acompanhar a extensão da doença. Quadros localizados podem ser manejados com higiene e terapia tópica apropriada; doença extensa, bolhosa ou complicada pode exigir tratamento sistêmico conforme protocolo.'},
 3: {'etiology': 'Streptococcus pneumoniae permanece uma associação bacteriana clássica na PAC típica, especialmente em apresentação aguda com febre, expectoração, dor pleurítica e achados focais. Isso orienta terapia empírica sem significar confirmação microbiológica.',
     'redflag': 'Queda de saturação, confusão e hipotensão representam disfunção fisiológica e possível sepse/insuficiência respiratória. Nessa situação, trocar apenas o antibiótico oral é insuficiente; o paciente precisa de estabilização e encaminhamento.',
     'return': 'Resposta clínica não é instantânea. Reavaliação em 48–72 horas, ou antes se houver piora, permite verificar adesão, evolução, complicações e necessidade de revisar o diagnóstico ou o tratamento.',
     'severity': 'Na pneumonia adquirida na comunidade, escolher o local de cuidado é tão importante quanto escolher o antimicrobiano. Frequência respiratória, saturação, pressão, estado mental, hidratação, comorbidades e suporte domiciliar ajudam a estimar gravidade.',
     'testing': 'Em PAC leve e estável, exames devem ser guiados por dúvida diagnóstica, gravidade, falha ou possibilidade de mudança de conduta. Oximetria é particularmente útil porque hipoxemia pode não ser evidente apenas pela ausculta.',
     'treatment': 'Na PAC ambulatorial, a escolha deve cobrir os agentes mais prováveis com o menor espectro eficaz, considerando alergias, comorbidades, resistência e protocolo local. Beta-lactâmicos como amoxicilina são opções de primeira linha em muitos cenários apropriados.'},
 4: {'etiology': 'Escherichia coli uropatogênica é o agente mais classicamente associado à cistite comunitária. Sua origem intestinal explica a proximidade ecológica entre colonização do períneo e ascensão ao trato urinário.',
     'pitfall': 'Nova parceria sexual, sangramento pós-coito, corrimento ou dor pélvica reabrem o diagnóstico diferencial para uretrite/cervicite e outras IST. Disúria não pertence exclusivamente à cistite.',
     'redflag': 'Febre alta, vômitos e dor lombar após sintomas urinários sugerem pielonefrite ou ITU complicada. O manejo deve ser reclassificado, incluindo cultura quando possível, avaliação de gravidade e capacidade de tratamento oral.',
     'syndrome': 'Disúria, urgência e polaciúria sugerem cistite, mas febre, dor lombar, vômitos, gestação, anomalia urológica e recorrência mudam o caso para maior risco ou outro nível de investigação.',
     'tests': 'Em cistite não complicada típica, o diagnóstico pode ser clínico. EAS e urocultura tornam-se mais importantes em gestação, recorrência, falha, apresentação atípica, suspeita de pielonefrite ou complicação.',
     'treatment': 'A escolha do antimicrobiano deve considerar se a infecção é realmente baixa, além de função renal, gestação, alergias, resistência local e padronização do SUS. Fármacos adequados para bexiga não são automaticamente adequados para parênquima renal.'},
 5: {'etiology': 'Klebsiella pneumoniae é uma enterobactéria capaz de causar ITU comunitária ou associada a cuidados de saúde e pode adquirir mecanismos importantes de resistência. O antibiograma, e não o nome do gênero, define sensibilidade.',
     'micro': 'Urocultura em pielonefrite/ITU complicada permite confirmar agente e ajustar terapia. Deve ser coletada antes do antibiótico quando isso for viável, mas nunca à custa de atrasar tratamento de paciente grave.',
     'risk': 'Diabetes, cálculo, obstrução, instrumentação e alterações anatômicas aumentam a chance de ITU complicada, falha terapêutica e necessidade de investigação adicional.',
     'severity': 'ITU febril com dor lombar deve ser tratada como possível pielonefrite até avaliação adequada. Sinais vitais, perfusão, estado mental, vômitos, hidratação e gestação definem risco imediato e possibilidade de tratamento ambulatorial.',
     'source': 'Infecção associada à obstrução urinária é uma emergência de controle de foco. Se o sistema coletor está obstruído, apenas aumentar antibiótico pode não resolver a pressão e o reservatório infectado.',
     'treatment': 'Taquicardia, vômitos e intolerância oral reduzem a segurança do tratamento domiciliar. Pode ser necessário suporte, antimicrobiano parenteral conforme protocolo e encaminhamento para maior complexidade.'},
 6: {'assessment': 'Em ferida crônica, mais secreção ou odor não bastam para diagnosticar infecção invasiva. A avaliação deve procurar mudança em relação ao basal, dor, eritema, calor, necrose, profundidade, perfusão e sinais sistêmicos.',
     'colonization': 'Bactérias podem estar presentes na superfície sem invadir tecido ou causar síndrome infecciosa. Tratar colonização com antibiótico sistêmico não melhora necessariamente a ferida e aumenta pressão seletiva.',
     'etiology': 'Pseudomonas aeruginosa torna-se mais plausível com umidade crônica, exposição a antibióticos, internações e determinados hospedeiros, mas cor e odor não confirmam etiologia.',
     'redflag': 'Dor desproporcional, necrose e progressão rápida levantam suspeita de infecção necrosante ou isquemia crítica. Essas condições exigem avaliação hospitalar/cirúrgica urgente e não devem aguardar cultura.',
     'sample': 'Quando a microbiologia realmente pode mudar conduta, amostras profundas ou tecido obtido após limpeza e técnica adequada representam melhor o foco do que secreção superficial.',
     'treatment': 'Antipseudomonas sistêmico deve ser reservado para infecção clinicamente relevante com risco ou evidência compatível. Tratar um swab superficial isolado favorece eventos adversos e resistência sem resolver fatores como isquemia, pressão ou biofilme.'},
 7: {'aps': 'Peritonite, coleção e sepse ultrapassam o escopo de tratamento exclusivamente domiciliar. A APS deve reconhecer risco, iniciar medidas de suporte possíveis e coordenar acesso rápido à atenção hospitalar.',
     'coverage': 'Infecção intra-abdominal complicada de origem colônica requer cobertura empírica proporcional para flora entérica relevante, incluindo anaeróbios e Gram-negativos, ajustada à gravidade e epidemiologia.',
     'etiology': 'Bacteroides fragilis integra a microbiota colônica e torna-se patogênico quando há quebra de barreira, como perfuração ou abscesso. Infecções intra-abdominais costumam ser polimicrobianas.',
     'redflag': 'Dor abdominal progressiva com febre após possível ruptura de víscera sugere abdome agudo infeccioso. Na APS, a prioridade é reconhecer peritonite, sepse e instabilidade e organizar transferência segura.',
     'sample': 'Anaeróbios são sensíveis à exposição ao oxigênio e a amostra deve representar o foco. Aspirado ou tecido profundo, coletado e transportado de modo apropriado, tem maior rendimento que swab superficial.',
     'source': 'Abscesso ou perfuração é um problema de fonte além de ser um problema de bactéria. Drenagem, reparo ou cirurgia, quando indicados, precisam acompanhar o antimicrobiano.'},
 8: {'biology': 'Mycobacterium tuberculosis possui parede rica em lipídios e ácidos micólicos, característica associada à álcool-ácido resistência e à necessidade de técnicas laboratoriais próprias. Seu crescimento lento também ajuda a explicar tratamento prolongado.',
     'diagnosis': 'No SUS, a investigação bacteriológica utiliza teste rápido molecular para TB ou baciloscopia, com cultura e teste de sensibilidade conforme algoritmo e situação clínica; radiografia é complementar.',
     'infection': 'A tuberculose pulmonar é transmitida principalmente por aerossóis contendo bacilos. Ventilação, redução de permanência desnecessária em áreas fechadas, etiqueta respiratória e uso de máscara conforme indicação reduzem risco.',
     'publichealth': 'TB exige cuidado individual e ação de saúde pública: notificação, testagem para HIV conforme protocolo, avaliação de contatos, acompanhamento de adesão e apoio para completar o esquema.',
     'recognition': 'Tosse persistente, emagrecimento, febre vespertina e sudorese noturna formam um conjunto clássico que deve disparar investigação de tuberculose, sobretudo em sintomático respiratório.',
     'treatment': 'Na TB pulmonar sensível sem situação especial, o SUS utiliza esquema combinado padronizado, com fase intensiva contendo rifampicina, isoniazida, pirazinamida e etambutol e fase de continuação conforme protocolo.'},
 9: {'biology': 'Mycoplasma pneumoniae não possui parede celular. Por isso, beta-lactâmicos, que agem na síntese de peptidoglicano, não têm alvo para atuar contra esse agente.',
     'pattern': 'Mycoplasma pneumoniae pode causar quadro respiratório subagudo, com tosse seca persistente e sinais auscultatórios menos exuberantes que a queixa. O padrão é sugestivo, mas não dispensa estratificação de gravidade nem diferenciais virais.',
     'reassess': 'Piora de dispneia ou queda de saturação após 48–72 horas exige reavaliar diagnóstico, adesão, complicações, resistência e gravidade. Apenas dobrar dose sem nova avaliação pode atrasar reconhecimento de falha importante.',
     'severity': 'Idade jovem não protege contra hipoxemia. Saturação, frequência respiratória, pressão, estado mental, hidratação e comorbidades continuam sendo a base para decidir manejo ambulatorial ou encaminhamento.',
     'tests': 'Em quadro leve e típico, o diagnóstico pode ser sindrômico. Testes moleculares e imagem ganham valor quando há gravidade, surto, dúvida diagnóstica, falha ou necessidade de distinguir outra condição.',
     'treatment': 'Quando há indicação de antimicrobiano e suspeita relevante de Mycoplasma, é necessário escolher fármaco com atividade contra agentes sem parede celular, conforme idade, gestação, contraindicações e protocolo local.'},
 10: {'complication': 'Dor pélvica com febre pode indicar doença inflamatória pélvica; dor testicular aguda exige avaliar epididimite e diagnósticos tempo-dependentes, incluindo torção. A complicação muda esquema e nível de urgência.',
      'etiology': 'Chlamydia trachomatis é bactéria intracelular obrigatória e causa uretrite e cervicite, frequentemente com poucos sintomas. Neisseria gonorrhoeae é diferencial importante e coinfecção pode ocorrer.',
      'history': 'A investigação de IST exige história sexual confidencial, respeitosa e sem julgamento, incluindo práticas, uso de preservativos, parceiros, sítios de exposição, gestação e sintomas de complicação.',
      'partners': 'Manejo de parcerias reduz reinfecção e transmissão. Elas devem ser avaliadas e tratadas conforme PCDT, com preservação de confidencialidade e oferta de prevenção/testagem.',
      'test': 'Testes de amplificação de ácidos nucleicos (NAAT) são métodos de escolha quando disponíveis, usando amostra validada para o sítio de exposição, como urina de primeiro jato ou swab apropriado.',
      'treatment': 'O PCDT-IST orienta tratamento antibiótico de clamídia conforme situação clínica, incluindo esquemas com doxiciclina ou azitromicina e adaptações para gestação e outras circunstâncias.'}}

QUALITY_TEACHING = {
    "BEST": "Você priorizou corretamente o problema clínico central deste momento.",
    "SUBOPTIMAL": "A alternativa tem fundamento, mas não é a melhor porque deixa de priorizar um elemento que muda segurança, efetividade ou uso racional de recursos.",
    "PLAUSIBLE": "A alternativa parece possível, porém confunde uma hipótese secundária com a prioridade clínica deste ponto da consulta.",
    "WRONG": "A alternativa se afasta do mecanismo, da síndrome ou da prioridade de segurança e poderia atrasar a conduta adequada.",
}


def _profile_index(case):
    order = int(case.order)
    return ((order - 1) // 2) + 1 if 1 <= order <= 20 else None


def _best(node):
    return next((item for item in node.get("options", []) if item.get("quality") == "BEST"), {})


@register.filter
def learning_note(node, case):
    if not node or not case:
        return {}
    profile = _profile_index(case)
    theory = THEORY.get(profile, {}).get(node.get("id"), "")
    best = _best(node)
    pearl = node.get("pearl") or ("Regra de bolso: " + best.get("text", "") if best else "")
    return {
        "theory": theory,
        "pearl": pearl,
        "pearl_basis": (
            "Esta pérola resume a consequência prática do princípio acima: reconhecer o mecanismo, "
            "a gravidade e o sítio da infecção ajuda a escolher a conduta proporcional e evita tanto "
            "subtratamento quanto uso desnecessário de exames ou antimicrobianos. " + theory
        ),
        "base": LEARNING_BASES.get(profile, ""),
    }


@register.filter
def best_option(node):
    return _best(node) if node else {}


@register.filter
def node_for_answer(answer, tree):
    if not answer or not tree:
        return {}
    return next((item for item in tree.get("nodes", []) if item.get("id") == answer.node_id), {})


@register.filter
def quality_teaching(answer):
    return QUALITY_TEACHING.get(answer.quality, "") if answer else ""


@register.filter
def is_best(answer):
    return bool(answer and answer.quality == "BEST")
