"""Alternativas calibradas para a árvore bacteriana.

Objetivos pedagógicos:
- manter comprimentos semelhantes dentro de cada ponto de decisão;
- evitar absolutos, caricaturas e pistas de prova;
- usar distratores clinicamente plausíveis para quem ainda não domina o conteúdo;
- preservar as quatro categorias de qualidade definidas em decision_trees.py.
"""

OPTION_TEXTS = {
    1: {
        "triage": {
            "BEST": "Avaliar sinais vitais, extensão, localização de risco, comorbidades e presença de flutuação ou coleção drenável.",
            "SUBOPTIMAL": "Examinar extensão, dor, temperatura e aspecto da lesão, programando revisão precoce conforme a evolução clínica.",
            "PLAUSIBLE": "Solicitar ultrassonografia da região para caracterizar a coleção antes de definir necessidade de procedimento ou antibiótico.",
            "WRONG": "Iniciar antibiótico oral contra cocos Gram-positivos e reavaliar em 48 horas antes de considerar drenagem.",
        },
        "etiology": {
            "BEST": "Staphylococcus aureus, pela associação frequente entre esse agente e abscessos cutâneos com conteúdo purulento.",
            "SUBOPTIMAL": "Streptococcus pyogenes, por ser causa importante de infecção cutânea, embora predomine em quadros menos purulentos.",
            "PLAUSIBLE": "Staphylococcus epidermidis, considerando sua presença habitual na pele e a possibilidade de invasão após ruptura da barreira.",
            "WRONG": "Pseudomonas aeruginosa, considerando que secreção purulenta e umidade local podem acompanhar algumas infecções cutâneas bacterianas.",
        },
        "procedure": {
            "BEST": "Realizar ou encaminhar para incisão e drenagem quando indicada, associando analgesia, curativo e orientação de retorno.",
            "SUBOPTIMAL": "Iniciar antibiótico contra cocos Gram-positivos e reavaliar precocemente a necessidade de drenagem da coleção acessível.",
            "PLAUSIBLE": "Realizar aspiração por agulha da coleção, associar antibiótico e reservar incisão para ausência de resposta clínica.",
            "WRONG": "Iniciar antibiótico e compressas mornas, reservando procedimento invasivo para persistência da coleção após alguns dias.",
        },
        "antibiotic": {
            "BEST": "Indicar antibiótico conforme extensão, sinais sistêmicos, fatores do hospedeiro e protocolo local após controle adequado do foco.",
            "SUBOPTIMAL": "Prescrever antibiótico de espectro estreito contra cocos Gram-positivos após drenagem, mesmo na ausência de fatores adicionais.",
            "PLAUSIBLE": "Aguardar cultura do material drenado antes de decidir antibiótico, mantendo curativo e reavaliação clínica precoce.",
            "WRONG": "Iniciar cobertura empírica mais ampla para Gram-positivos resistentes e Gram-negativos após a drenagem do abscesso.",
        },
        "culture": {
            "BEST": "Reservar cultura para recorrência, falha terapêutica, gravidade ou risco de resistência, priorizando material representativo da coleção.",
            "SUBOPTIMAL": "Coletar cultura durante toda drenagem de abscesso, mesmo quando o caso é simples e evolui favoravelmente.",
            "PLAUSIBLE": "Coletar swab da secreção espontânea antes do procedimento, utilizando o resultado para ajustar eventual antimicrobiano.",
            "WRONG": "Adiar investigação microbiológica para um segundo episódio, pois a primeira ocorrência costuma responder ao manejo empírico.",
        },
        "followup": {
            "BEST": "Orientar retorno precoce diante de febre, expansão do eritema, dor desproporcional, piora geral ou nova coleção.",
            "SUBOPTIMAL": "Programar revisão em 48 a 72 horas para avaliar dor, secreção e cicatrização, antecipando se houver piora.",
            "PLAUSIBLE": "Orientar retorno ao final de sete dias se persistirem secreção, vermelhidão ou dificuldade de cicatrização local.",
            "WRONG": "Manter autocuidado e retornar após concluir o tratamento prescrito, salvo se a dor impedir atividades habituais.",
        },
    },
    2: {
        "recognition": {
            "BEST": "Considerar impetigo e avaliar extensão, presença de bolhas, celulite, febre e ocorrência de casos entre contatos.",
            "SUBOPTIMAL": "Considerar dermatite com infecção bacteriana secundária e examinar outras áreas da pele em busca de lesões semelhantes.",
            "PLAUSIBLE": "Considerar picadas de insetos com impetiginização secundária e investigar exposição recente e padrão de distribuição das lesões.",
            "WRONG": "Considerar herpes simples disseminado em pele previamente íntegra e procurar vesículas recentes entre as áreas crostosas.",
        },
        "etiology": {
            "BEST": "Staphylococcus aureus, com possível participação de estreptococos beta-hemolíticos nas lesões superficiais típicas de impetigo.",
            "SUBOPTIMAL": "Streptococcus pyogenes como agente predominante, reconhecendo que cocos Gram-positivos são causas frequentes dessa síndrome cutânea.",
            "PLAUSIBLE": "Staphylococcus aureus isoladamente, relacionando a formação das crostas à colonização e invasão superficial da epiderme.",
            "WRONG": "Pseudomonas aeruginosa, relacionando a umidade das lesões superficiais à possibilidade de proliferação de bacilos Gram-negativos.",
        },
        "testing": {
            "BEST": "Fazer diagnóstico clínico no episódio típico e reservar cultura para falha, recorrência, surto ou apresentação mais extensa.",
            "SUBOPTIMAL": "Iniciar manejo clínico e solicitar cultura se não houver melhora esperada nos primeiros dias de tratamento.",
            "PLAUSIBLE": "Coletar cultura de uma lesão representativa na primeira consulta para escolher terapia tópica ou sistêmica com maior precisão.",
            "WRONG": "Solicitar hemograma e proteína C reativa para decidir entre tratamento tópico e antibiótico por via oral.",
        },
        "treatment": {
            "BEST": "Associar higiene local e terapia tópica apropriada nas poucas lesões, reservando tratamento sistêmico para maior extensão ou complicação.",
            "SUBOPTIMAL": "Iniciar antibiótico oral de espectro estreito contra cocos Gram-positivos mesmo com poucas lesões e ausência de febre.",
            "PLAUSIBLE": "Realizar higiene cuidadosa e usar antisséptico local, reavaliando antes de acrescentar antimicrobiano específico às lesões.",
            "WRONG": "Utilizar combinação tópica de antibiótico e corticoide para reduzir simultaneamente carga bacteriana, inflamação e prurido local.",
        },
        "prevention": {
            "BEST": "Reforçar higiene das mãos, não compartilhar objetos pessoais, manter unhas curtas e avaliar contatos que desenvolvam lesões semelhantes.",
            "SUBOPTIMAL": "Separar toalhas e utensílios pessoais, cobrir as lesões e reforçar higiene cotidiana até a melhora clínica.",
            "PLAUSIBLE": "Orientar descolonização nasal dos moradores da casa quando houver um segundo caso, mesmo sem recorrências documentadas.",
            "WRONG": "Prescrever antimicrobiano tópico preventivo para contatos próximos durante alguns dias, associado às medidas habituais de higiene.",
        },
        "alarm": {
            "BEST": "Reavaliar prontamente para celulite ou infecção mais profunda, estimando gravidade e necessidade de modificar o nível de cuidado.",
            "SUBOPTIMAL": "Iniciar terapia sistêmica contra cocos Gram-positivos e programar reavaliação muito precoce para confirmar resposta ao tratamento.",
            "PLAUSIBLE": "Coletar cultura da borda ativa e aguardar o resultado por curto período antes de ampliar o tratamento antimicrobiano.",
            "WRONG": "Intensificar o tratamento tópico e observar por 48 horas, pois inflamação periférica pode acompanhar a evolução das crostas.",
        },
    },
    3: {
        "severity": {
            "BEST": "Avaliar frequência respiratória, saturação, pressão, estado mental, hidratação, comorbidades e condições para cuidado domiciliar seguro.",
            "SUBOPTIMAL": "Avaliar ausculta, temperatura, frequência respiratória e saturação, utilizando esses dados para decidir manejo inicial ambulatorial.",
            "PLAUSIBLE": "Solicitar radiografia de tórax inicialmente e utilizar a extensão radiológica para definir gravidade e necessidade de encaminhamento.",
            "WRONG": "Escolher o esquema antimicrobiano pelo perfil clínico e pelas comorbidades, avaliando gravidade pela resposta nas primeiras horas.",
        },
        "etiology": {
            "BEST": "Streptococcus pneumoniae, pela associação clássica com pneumonia comunitária aguda, febre, expectoração, dor pleurítica e achados focais.",
            "SUBOPTIMAL": "Haemophilus influenzae, agente possível de pneumonia comunitária e mais frequente em alguns pacientes com doença pulmonar crônica.",
            "PLAUSIBLE": "Mycoplasma pneumoniae, agente comunitário relevante, embora frequentemente associado a apresentação mais subaguda e menos produtiva.",
            "WRONG": "Staphylococcus aureus, agente capaz de causar pneumonia comunitária, mas geralmente relacionado a contextos epidemiológicos ou fatores específicos.",
        },
        "testing": {
            "BEST": "Usar clínica e gravidade para selecionar imagem e laboratório quando houver dúvida, falha terapêutica ou possível mudança de cuidado.",
            "SUBOPTIMAL": "Solicitar radiografia de tórax quando disponível, sem atrasar tratamento de paciente estável com quadro clínico suficientemente característico.",
            "PLAUSIBLE": "Solicitar radiografia e exames inflamatórios na primeira avaliação para documentar extensão e estabelecer um valor basal de acompanhamento.",
            "WRONG": "Coletar cultura de escarro antes do tratamento em paciente ambulatorial estável para direcionar o antimicrobiano desde o início.",
        },
        "treatment": {
            "BEST": "Escolher esquema oral de primeira linha com espectro adequado ao pneumococo, ajustado ao protocolo local e ao perfil clínico.",
            "SUBOPTIMAL": "Usar amoxicilina com clavulanato para ampliar cobertura respiratória, mesmo sem fator clínico específico que justifique esse espectro.",
            "PLAUSIBLE": "Utilizar macrolídeo em monoterapia para cobrir simultaneamente pneumococo e agentes atípicos em paciente ambulatorial de baixo risco.",
            "WRONG": "Iniciar fluoroquinolona respiratória como terapia empírica inicial para maximizar cobertura bacteriana e simplificar o esquema por via oral.",
        },
        "return": {
            "BEST": "Orientar sinais de alarme e reavaliar em 48 a 72 horas, antecipando diante de dispneia ou piora do estado geral.",
            "SUBOPTIMAL": "Programar retorno em 72 horas para avaliar febre, tosse e tolerância ao tratamento, com orientação de procurar antes se piorar.",
            "PLAUSIBLE": "Programar retorno ao final de cinco a sete dias, desde que não apareçam febre persistente ou aumento importante da dispneia.",
            "WRONG": "Orientar retorno após concluir o antimicrobiano, antecipando somente diante de dor torácica intensa ou intolerância aos medicamentos.",
        },
        "redflag": {
            "BEST": "Reconhecer pneumonia grave e providenciar encaminhamento emergencial, oferecendo suporte inicial conforme os recursos disponíveis na unidade.",
            "SUBOPTIMAL": "Iniciar oxigênio e tratamento parenteral disponível, observando resposta inicial enquanto organiza avaliação em serviço de maior complexidade.",
            "PLAUSIBLE": "Trocar para antimicrobiano oral de maior espectro e organizar reavaliação hospitalar no mesmo dia se não houver estabilização.",
            "WRONG": "Solicitar imagem urgente e exames laboratoriais ambulatoriais antes da transferência para definir se a alteração hemodinâmica é infecciosa.",
        },
    },
    4: {
        "syndrome": {
            "BEST": "Investigar febre, dor lombar, vômitos, gestação, alteração urológica e recorrência para identificar infecção alta ou complicada.",
            "SUBOPTIMAL": "Investigar hematúria, episódios prévios, diabetes e uso recente de antimicrobianos para estimar recorrência e resistência bacteriana.",
            "PLAUSIBLE": "Investigar corrimento, nova parceria sexual, dor pélvica e sangramento para diferenciar cistite de uretrite ou cervicite.",
            "WRONG": "Investigar exposição recente a antibióticos e resultados de culturas anteriores para estimar a probabilidade de resistência do uropatógeno.",
        },
        "etiology": {
            "BEST": "Escherichia coli uropatogênica, agente mais classicamente associado à cistite comunitária não complicada nesse padrão clínico.",
            "SUBOPTIMAL": "Klebsiella pneumoniae, enterobactéria capaz de causar cistite comunitária, embora menos frequente nesse cenário típico inicial.",
            "PLAUSIBLE": "Staphylococcus saprophyticus, agente reconhecido de cistite comunitária, especialmente em determinados grupos de mulheres jovens.",
            "WRONG": "Enterococcus faecalis, uropatógeno possível em situações específicas, porém menos compatível com a apresentação comunitária não complicada descrita.",
        },
        "tests": {
            "BEST": "Admitir diagnóstico clínico no quadro típico e usar EAS ou cultura quando houver dúvida, recorrência, gestação ou complicação.",
            "SUBOPTIMAL": "Solicitar EAS quando estiver prontamente disponível e iniciar manejo conforme sintomas, fatores de risco e resultado obtido.",
            "PLAUSIBLE": "Coletar urocultura antes do tratamento em todo primeiro episódio, mas iniciar terapia no mesmo dia sem aguardar o resultado.",
            "WRONG": "Solicitar EAS e urocultura na primeira consulta de todos os casos para confirmar etiologia antes de definir o esquema completo.",
        },
        "treatment": {
            "BEST": "Escolher antimicrobiano oral de primeira linha conforme protocolo local, resistência, função renal, alergias, gestação e sítio da infecção.",
            "SUBOPTIMAL": "Utilizar nitrofurantoína quando o quadro for restrito à bexiga e não houver contraindicação clínica ou farmacológica relevante.",
            "PLAUSIBLE": "Utilizar sulfametoxazol-trimetoprima quando não houver contraindicação e o padrão local de resistência permitir essa escolha empírica.",
            "WRONG": "Preferir fluoroquinolona oral pela boa penetração urinária e pela cobertura ampla de enterobactérias em tratamento ambulatorial inicial.",
        },
        "pitfall": {
            "BEST": "Reabrir o diferencial para uretrite ou cervicite, fazendo história sexual respeitosa e investigação de IST conforme protocolo.",
            "SUBOPTIMAL": "Manter cistite como hipótese inicial, mas perguntar sobre corrimento, dor pélvica e exposições antes de definir a conduta.",
            "PLAUSIBLE": "Solicitar urocultura e manter o tratamento urinário até esclarecer se os novos achados representam outra causa de disúria.",
            "WRONG": "Ampliar cobertura para outro uropatógeno e reavaliar em 48 horas, investigando IST se os sintomas geniturinários persistirem.",
        },
        "redflag": {
            "BEST": "Reclassificar como possível pielonefrite ou ITU complicada, colher cultura quando viável e avaliar necessidade de encaminhamento.",
            "SUBOPTIMAL": "Trocar para antimicrobiano oral com penetração renal adequada e organizar reavaliação precoce se o paciente permanecer estável.",
            "PLAUSIBLE": "Coletar cultura, iniciar tratamento oral para pielonefrite e decidir encaminhamento conforme resposta clínica nas primeiras horas.",
            "WRONG": "Manter o esquema de cistite enquanto aguarda cultura, acrescentando antiemético e hidratação se a tolerância oral permitir.",
        },
    },
    5: {
        "severity": {
            "BEST": "Avaliar sinais vitais, perfusão, estado mental, vômitos, hidratação, gestação e critérios clínicos de sepse ou instabilidade.",
            "SUBOPTIMAL": "Avaliar temperatura, frequência cardíaca, pressão, punho-percussão lombar e tolerância oral para estimar gravidade do episódio.",
            "PLAUSIBLE": "Solicitar hemograma, creatinina e ultrassonografia precocemente, usando os resultados para decidir necessidade de tratamento hospitalar.",
            "WRONG": "Avaliar febre, intensidade da dor e tolerância oral, iniciando tratamento ambulatorial se esses parâmetros parecerem controláveis.",
        },
        "risk": {
            "BEST": "Considerar ITU complicada, possível obstrução, maior risco de falha e necessidade de cultura, imagem ou encaminhamento conforme evolução.",
            "SUBOPTIMAL": "Considerar maior risco de recorrência e resistência bacteriana, planejando cultura e seguimento mais próximo durante o tratamento.",
            "PLAUSIBLE": "Considerar maior probabilidade de enterobactéria resistente, incluindo Klebsiella, e escolher cobertura empírica mais ampla desde o início.",
            "WRONG": "Considerar principalmente ajuste de dose pela função renal, sem modificar de forma relevante a classificação clínica da infecção urinária.",
        },
        "micro": {
            "BEST": "Coletar urocultura antes do antimicrobiano quando viável, iniciar tratamento indicado sem atraso e ajustar depois pelo antibiograma.",
            "SUBOPTIMAL": "Coletar EAS e urocultura e iniciar terapia empírica no mesmo atendimento, refinando o esquema quando houver resultado microbiológico.",
            "PLAUSIBLE": "Administrar a primeira dose do antimicrobiano e coletar urocultura logo depois para evitar atraso em paciente com maior risco.",
            "WRONG": "Iniciar terapia empírica e reservar urocultura para ausência de melhora em 48 horas, reduzindo exames na fase inicial.",
        },
        "etiology": {
            "BEST": "Interpretar Klebsiella como enterobactéria uropatogênica com potencial de resistência e ajustar terapia conforme sensibilidade e contexto clínico.",
            "SUBOPTIMAL": "Considerar Klebsiella compatível com ITU complicada e utilizar o antibiograma para refinar a escolha após terapia empírica inicial.",
            "PLAUSIBLE": "Interpretar o isolamento como sugestivo de mecanismo de resistência relevante e ampliar cobertura até conhecer o antibiograma completo.",
            "WRONG": "Interpretar Klebsiella como marcador de aquisição relacionada à assistência e conduzir o caso inicialmente como infecção hospitalar.",
        },
        "treatment": {
            "BEST": "Encaminhar para maior complexidade, iniciar suporte e antimicrobiano empírico conforme gravidade, ajustando posteriormente à cultura disponível.",
            "SUBOPTIMAL": "Administrar primeira dose parenteral prevista no protocolo, oferecer suporte e organizar transferência imediata para continuidade do cuidado.",
            "PLAUSIBLE": "Controlar vômitos, iniciar antimicrobiano oral com boa penetração renal e reavaliar em poucas horas antes de encaminhar.",
            "WRONG": "Usar antimicrobiano oral de espectro ampliado após antiemético e manter observação ambulatorial até confirmar tolerância às primeiras doses.",
        },
        "source": {
            "BEST": "Reconhecer que infecção com obstrução pode exigir descompressão urgente, pois antimicrobiano isolado pode não controlar adequadamente o foco.",
            "SUBOPTIMAL": "Solicitar imagem prioritária e discutir avaliação urológica ou hospitalar conforme evidência de obstrução e repercussão clínica encontrada.",
            "PLAUSIBLE": "Iniciar antimicrobiano e medicamento expulsivo, realizando imagem rapidamente para decidir necessidade de intervenção urológica posterior.",
            "WRONG": "Intensificar antimicrobiano, analgesia e hidratação enquanto aguarda eliminação do cálculo, encaminhando se persistirem febre ou obstrução.",
        },
    },
    6: {
        "assessment": {
            "BEST": "Comparar com o basal e avaliar dor, eritema, calor, necrose, sinais sistêmicos, perfusão, profundidade e extensão da ferida.",
            "SUBOPTIMAL": "Medir e fotografar a ferida, registrar secreção, odor e bordas e programar reavaliação clínica em intervalo curto.",
            "PLAUSIBLE": "Coletar material da secreção antes da limpeza para identificar o agente e depois completar avaliação do leito da ferida.",
            "WRONG": "Iniciar tratamento antimicrobiano pela mudança de odor e secreção, usando a evolução clínica para confirmar se havia infecção.",
        },
        "colonization": {
            "BEST": "Diferenciar colonização de infecção invasiva pelo quadro clínico, evitando tratar sistemicamente um resultado microbiológico isolado da superfície.",
            "SUBOPTIMAL": "Priorizar cuidado local da ferida e reavaliar, reservando antibiótico sistêmico para surgimento de sinais clínicos de infecção.",
            "PLAUSIBLE": "Usar antimicrobiano tópico dirigido ao resultado do swab, mantendo tratamento sistêmico reservado para sinais de progressão local.",
            "WRONG": "Iniciar antibiótico sistêmico dirigido ao swab positivo para reduzir carga bacteriana e prevenir evolução para infecção invasiva.",
        },
        "sample": {
            "BEST": "Obter tecido ou amostra profunda após limpeza e técnica adequada quando o resultado microbiológico puder modificar a conduta terapêutica.",
            "SUBOPTIMAL": "Coletar swab após limpeza usando técnica padronizada quando amostra profunda não estiver disponível e houver indicação clínica.",
            "PLAUSIBLE": "Coletar swab da área mais viável do leito após irrigação, evitando regiões necróticas e secreção acumulada superficialmente.",
            "WRONG": "Coletar secreção externa antes da limpeza para aumentar a quantidade de material e melhorar a chance de crescimento bacteriano.",
        },
        "etiology": {
            "BEST": "Considerar Pseudomonas mais plausível pelos fatores de risco, sem confirmar etiologia pela cor, odor ou aparência da secreção.",
            "SUBOPTIMAL": "Incluir Pseudomonas no diagnóstico diferencial e buscar sinais clínicos que indiquem se existe realmente infecção do tecido.",
            "PLAUSIBLE": "Considerar secreção esverdeada e odor característico como forte evidência presuntiva de Pseudomonas enquanto aguarda confirmação microbiológica.",
            "WRONG": "Assumir Pseudomonas como agente provável pelos antibióticos prévios e pela umidade crônica, iniciando cobertura antes da cultura.",
        },
        "treatment": {
            "BEST": "Evitar antipseudomonas sistêmico baseado apenas no swab, otimizar cuidado da ferida, perfusão, pressão e fatores predisponentes.",
            "SUBOPTIMAL": "Reavaliar sinais clínicos e obter amostra mais representativa antes de decidir tratamento sistêmico dirigido para Pseudomonas aeruginosa.",
            "PLAUSIBLE": "Usar antisséptico ou agente tópico com atividade local e acompanhar evolução, reservando tratamento sistêmico para progressão clínica.",
            "WRONG": "Iniciar ciprofloxacino oral dirigido ao isolamento de Pseudomonas e reavaliar a ferida após alguns dias de tratamento.",
        },
        "redflag": {
            "BEST": "Suspeitar infecção necrosante ou isquemia grave e encaminhar emergencialmente para avaliação hospitalar e cirúrgica sem atrasos evitáveis.",
            "SUBOPTIMAL": "Iniciar antimicrobiano de amplo espectro e suporte disponível enquanto organiza transferência imediata para avaliação cirúrgica hospitalar.",
            "PLAUSIBLE": "Solicitar imagem e exames laboratoriais com prioridade no mesmo dia para delimitar extensão antes de decidir abordagem cirúrgica.",
            "WRONG": "Realizar desbridamento ambulatorial possível, iniciar antimicrobiano amplo e programar revisão em 24 horas para verificar progressão.",
        },
    },
    7: {
        "redflag": {
            "BEST": "Avaliar instabilidade, peritonismo e sepse e organizar encaminhamento hospitalar urgente, oferecendo suporte inicial conforme recursos disponíveis.",
            "SUBOPTIMAL": "Completar exame abdominal e sinais vitais imediatamente e encaminhar se houver peritonismo, instabilidade ou deterioração clínica relevante.",
            "PLAUSIBLE": "Iniciar analgesia, hidratação e exames laboratoriais básicos antes da referência, buscando caracterizar melhor gravidade e provável foco abdominal.",
            "WRONG": "Iniciar antimicrobiano oral e solicitar imagem urgente em regime ambulatorial, encaminhando se houver confirmação de coleção ou perfuração.",
        },
        "etiology": {
            "BEST": "Bacteroides fragilis integra a microbiota colônica e pode causar infecção quando a barreira intestinal é rompida em perfuração ou abscesso.",
            "SUBOPTIMAL": "Bacteroides fragilis participa da flora intestinal e pode integrar infecções polimicrobianas após contaminação da cavidade abdominal.",
            "PLAUSIBLE": "Bacteroides fragilis ganha importância após antibióticos prévios, que podem selecionar anaeróbios resistentes dentro da microbiota intestinal habitual.",
            "WRONG": "Bacteroides fragilis pode atravessar mucosa intestinal íntegra durante inflamação sistêmica e alcançar a cavidade abdominal por disseminação hematogênica.",
        },
        "sample": {
            "BEST": "Coletar aspirado ou tecido profundo e transportar adequadamente para preservar anaeróbios, representando diretamente o foco infeccioso abdominal.",
            "SUBOPTIMAL": "Enviar material profundo da coleção seguindo orientação do laboratório e minimizando exposição ao oxigênio durante coleta e transporte.",
            "PLAUSIBLE": "Coletar material pelo dreno logo após sua colocação, antes de grande exposição ambiental, para cultura aeróbia e anaeróbia.",
            "WRONG": "Priorizar hemoculturas antes da drenagem, utilizando o crescimento sanguíneo para definir a composição microbiológica do abscesso abdominal.",
        },
        "source": {
            "BEST": "Combinar antimicrobiano com controle de foco quando indicado, por drenagem ou procedimento cirúrgico da coleção intra-abdominal.",
            "SUBOPTIMAL": "Iniciar cobertura antimicrobiana adequada e solicitar avaliação cirúrgica precoce para decidir a melhor estratégia de controle de foco.",
            "PLAUSIBLE": "Ampliar cobertura antimicrobiana e observar resposta inicial por curto período antes de indicar drenagem de uma coleção localizada.",
            "WRONG": "Realizar exames de imagem seriados durante terapia antimicrobiana e reservar intervenção para aumento documentado da coleção abdominal.",
        },
        "coverage": {
            "BEST": "Cobrir Gram-negativos entéricos e anaeróbios conforme gravidade, epidemiologia e protocolo hospitalar, reduzindo espectro quando houver dados microbiológicos.",
            "SUBOPTIMAL": "Escolher combinação com atividade contra enterobactérias e anaeróbios, ajustando doses e duração conforme controle do foco e evolução.",
            "PLAUSIBLE": "Iniciar carbapenêmico como cobertura empírica para flora entérica e anaeróbios, refinando o esquema depois dos resultados microbiológicos.",
            "WRONG": "Utilizar metronidazol como monoterapia inicial por sua atividade contra anaeróbios predominantes nas infecções de origem colônica.",
        },
        "aps": {
            "BEST": "Explicar necessidade de avaliação hospitalar diante de peritonite, coleção ou sepse e coordenar transferência após suporte inicial possível.",
            "SUBOPTIMAL": "Estabilizar com medidas disponíveis na APS e organizar avaliação hospitalar no mesmo dia para decidir procedimento e terapia definitiva.",
            "PLAUSIBLE": "Administrar primeira dose de antimicrobiano e solicitar imagem urgente antes da referência se o paciente estiver hemodinamicamente estável.",
            "WRONG": "Iniciar combinação antimicrobiana oral e organizar reavaliação em 24 horas, encaminhando se surgirem sinais sistêmicos de deterioração.",
        },
    },
    8: {
        "recognition": {
            "BEST": "Investigar tuberculose pulmonar ativamente, mantendo diagnósticos diferenciais e avaliação de gravidade diante do conjunto de sintomas crônicos.",
            "SUBOPTIMAL": "Investigar pneumonia bacteriana de evolução prolongada, mantendo tuberculose no diferencial caso não haja resposta ao tratamento inicial.",
            "PLAUSIBLE": "Investigar micose pulmonar ou outra infecção granulomatosa, considerando emagrecimento, tosse prolongada e sintomas constitucionais persistentes.",
            "WRONG": "Investigar neoplasia pulmonar inicialmente e acrescentar pesquisa de tuberculose se imagem ou evolução sugerirem processo infeccioso crônico.",
        },
        "infection": {
            "BEST": "Aplicar controle respiratório do serviço, favorecer ventilação, reduzir espera e orientar etiqueta respiratória e máscara conforme indicação.",
            "SUBOPTIMAL": "Manter o paciente em área ventilada, reduzir permanência em ambiente coletivo e reforçar etiqueta respiratória durante a investigação.",
            "PLAUSIBLE": "Oferecer máscara cirúrgica ao paciente e manter fluxo habitual da unidade, desde que permaneça afastado fisicamente de outros usuários.",
            "WRONG": "Reservar precauções respiratórias mais específicas para depois da confirmação microbiológica, mantendo ventilação e etiqueta respiratória enquanto investiga.",
        },
        "diagnosis": {
            "BEST": "Priorizar teste rápido molecular quando disponível, complementando com baciloscopia, cultura e sensibilidade conforme algoritmo e situação clínica.",
            "SUBOPTIMAL": "Solicitar baciloscopia e radiografia, acrescentando teste molecular conforme disponibilidade e necessidade de esclarecer resistência ou diagnóstico.",
            "PLAUSIBLE": "Solicitar radiografia e duas amostras para baciloscopia antes do teste molecular, utilizando o resultado inicial para ordenar os demais exames.",
            "WRONG": "Solicitar cultura de escarro como exame etiológico inicial e aguardar crescimento antes de definir necessidade de teste molecular complementar.",
        },
        "biology": {
            "BEST": "Relacionar parede rica em ácidos micólicos e crescimento lento à álcool-ácido resistência, diagnóstico específico e tratamento prolongado.",
            "SUBOPTIMAL": "Reconhecer bacilo álcool-ácido resistente de crescimento lento, característica relevante para métodos laboratoriais e duração do tratamento.",
            "PLAUSIBLE": "Relacionar persistência intracelular em macrófagos à dificuldade de erradicação, necessidade de combinação farmacológica e tratamento prolongado.",
            "WRONG": "Relacionar ausência funcional de peptidoglicano e metabolismo lento à baixa atividade dos beta-lactâmicos durante a infecção pulmonar.",
        },
        "treatment": {
            "BEST": "Iniciar esquema básico padronizado pelo SUS com rifampicina, isoniazida, pirazinamida e etambutol, acompanhando adesão e eventos adversos.",
            "SUBOPTIMAL": "Iniciar o esquema básico combinado do SUS e monitorar adesão, toxicidade e resposta clínica durante todas as fases terapêuticas.",
            "PLAUSIBLE": "Usar rifampicina, isoniazida e pirazinamida inicialmente em paciente de baixo risco para resistência, acrescentando etambutol se necessário.",
            "WRONG": "Iniciar esquema contendo fluoroquinolona junto a rifampicina e isoniazida para ampliar atividade enquanto aguarda perfil de sensibilidade.",
        },
        "publichealth": {
            "BEST": "Realizar notificação, testagem para HIV conforme protocolo, avaliação de contatos, apoio à adesão e seguimento longitudinal no território.",
            "SUBOPTIMAL": "Avaliar contatos domiciliares, acompanhar adesão e organizar seguimento pela equipe, acrescentando outras ações conforme risco identificado.",
            "PLAUSIBLE": "Notificar e oferecer testagem para HIV, deixando investigação de contatos para depois da confirmação de maior potencial de transmissão.",
            "WRONG": "Concentrar inicialmente o cuidado no paciente e iniciar investigação de contatos após a fase intensiva, quando houver resposta documentada.",
        },
    },
    9: {
        "pattern": {
            "BEST": "Considerar pneumonia por agentes atípicos, incluindo Mycoplasma, mantendo diferenciais e estratificação de gravidade apesar do bom estado geral.",
            "SUBOPTIMAL": "Considerar infecção viral respiratória e manter pneumonia atípica no diferencial, acompanhando sinais de gravidade e evolução da tosse.",
            "PLAUSIBLE": "Considerar coqueluche diante da tosse persistente e investigar características paroxísticas, contatos e situação vacinal antes de tratar.",
            "WRONG": "Considerar pneumonia pneumocócica de apresentação inicial pouco produtiva e escolher manejo empírico conforme gravidade e achados pulmonares.",
        },
        "severity": {
            "BEST": "Avaliar saturação, frequência respiratória, pressão, estado mental, hidratação e comorbidades antes de definir o local de cuidado.",
            "SUBOPTIMAL": "Avaliar saturação, frequência respiratória, temperatura e ausculta, acrescentando outros dados se houver qualquer sinal de instabilidade.",
            "PLAUSIBLE": "Solicitar radiografia de tórax primeiro e utilizar extensão do infiltrado para decidir necessidade de investigação e tratamento hospitalar.",
            "WRONG": "Solicitar hemograma e marcador inflamatório inicialmente e usar sua intensidade para estimar gravidade em paciente jovem e estável.",
        },
        "biology": {
            "BEST": "Reconhecer ausência de parede celular, o que elimina o alvo dos beta-lactâmicos e torna esses fármacos ineficazes contra Mycoplasma.",
            "SUBOPTIMAL": "Reconhecer bactéria pequena sem parede celular, característica estrutural que modifica a escolha de antimicrobianos para tratamento dirigido.",
            "PLAUSIBLE": "Relacionar localização predominantemente intracelular à baixa penetração de beta-lactâmicos e à preferência por antimicrobianos com ação intracelular.",
            "WRONG": "Relacionar produção constitutiva de beta-lactamase à resistência natural às penicilinas e cefalosporinas durante a infecção respiratória.",
        },
        "tests": {
            "BEST": "Usar diagnóstico clínico sindrômico em caso leve e reservar testes ou imagem para gravidade, surto, dúvida ou mudança de conduta.",
            "SUBOPTIMAL": "Solicitar radiografia quando houver dúvida diagnóstica ou evolução inesperada, mantendo avaliação clínica como base da decisão terapêutica.",
            "PLAUSIBLE": "Solicitar painel molecular respiratório no primeiro atendimento para diferenciar agente atípico de vírus e orientar escolha antimicrobiana.",
            "WRONG": "Solicitar Gram e cultura de escarro como investigação inicial, acrescentando teste molecular se a microbiologia convencional não esclarecer o agente.",
        },
        "treatment": {
            "BEST": "Escolher antimicrobiano ativo contra agentes atípicos conforme protocolo, idade e contraindicações, evitando beta-lactâmico isolado como terapia dirigida.",
            "SUBOPTIMAL": "Considerar macrolídeo ou doxiciclina conforme idade, contraindicações e protocolo local para cobrir Mycoplasma em tratamento ambulatorial.",
            "PLAUSIBLE": "Associar amoxicilina com clavulanato a macrolídeo para cobrir simultaneamente agentes típicos e atípicos durante o tratamento empírico.",
            "WRONG": "Utilizar ceftriaxona como monoterapia inicial por seu espectro respiratório ampliado e boa atividade contra bactérias comunitárias frequentes.",
        },
        "reassess": {
            "BEST": "Reavaliar diagnóstico e gravidade imediatamente e encaminhar conforme hipoxemia, dispneia, comorbidades e capacidade de suporte disponível.",
            "SUBOPTIMAL": "Rever adesão, tratamento e sinais de gravidade e organizar avaliação em maior complexidade se a saturação permanecer reduzida.",
            "PLAUSIBLE": "Trocar o antimicrobiano ativo para outra classe e programar nova avaliação no mesmo dia após observar resposta inicial.",
            "WRONG": "Prolongar o tratamento atual e reavaliar em 48 a 72 horas, pois a tosse por Mycoplasma costuma persistir.",
        },
    },
    10: {
        "history": {
            "BEST": "Fazer história sexual confidencial sobre práticas, preservativo, sintomas, gestação, sítios de exposição e outras possíveis infecções associadas.",
            "SUBOPTIMAL": "Perguntar sobre nova parceria, uso de preservativo, corrimento e dor pélvica ou testicular antes de escolher exames.",
            "PLAUSIBLE": "Priorizar sintomas urinários, método contraceptivo e antecedentes ginecológicos ou urológicos, acrescentando história sexual se surgirem achados sugestivos.",
            "WRONG": "Realizar inicialmente exames geniturinários e abordar história sexual detalhada depois de obter algum resultado objetivo que sugira IST.",
        },
        "etiology": {
            "BEST": "Chlamydia trachomatis, agente frequente de uretrite e cervicite, inclusive com sintomas discretos ou apresentações pouco específicas.",
            "SUBOPTIMAL": "Neisseria gonorrhoeae, diagnóstico diferencial importante e possível coinfecção diante de quadro de uretrite ou cervicite.",
            "PLAUSIBLE": "Mycoplasma genitalium, agente capaz de causar uretrite e cervicite e relevante sobretudo em persistência ou recorrência clínica.",
            "WRONG": "Escherichia coli, agente frequente de sintomas urinários e possível explicação alternativa para disúria sem sinais de infecção alta.",
        },
        "test": {
            "BEST": "Solicitar teste molecular de amplificação de ácidos nucleicos em amostra validada para cada sítio de exposição conforme protocolo.",
            "SUBOPTIMAL": "Solicitar NAAT em urina de primeiro jato ou swab apropriado, sem explorar sistematicamente outros sítios de exposição.",
            "PLAUSIBLE": "Solicitar NAAT em urina de primeiro jato para todos os pacientes e acrescentar swabs apenas se houver sintomas locais.",
            "WRONG": "Solicitar EAS e urocultura inicialmente e reservar NAAT para casos com piúria sem crescimento bacteriano na cultura convencional.",
        },
        "treatment": {
            "BEST": "Tratar conforme PCDT-IST vigente, escolhendo esquema recomendado conforme situação clínica ou gestação e abordando prevenção e parcerias.",
            "SUBOPTIMAL": "Usar esquema recomendado para clamídia e programar seguimento, deixando situações especiais e manejo de parcerias para consulta posterior.",
            "PLAUSIBLE": "Usar doxiciclina como esquema inicial para clamídia e modificar a escolha depois se surgirem contraindicação ou informação de gestação.",
            "WRONG": "Utilizar ceftriaxona como monoterapia inicial para cobrir uretrite bacteriana frequente e ajustar após confirmação etiológica do agente.",
        },
        "partners": {
            "BEST": "Orientar avaliação e manejo das parcerias conforme PCDT, oferecendo prevenção e testagem para outras IST quando indicada.",
            "SUBOPTIMAL": "Orientar comunicação à parceria e uso de preservativo até completar o manejo, encaminhando-a para avaliação clínica e testagem.",
            "PLAUSIBLE": "Orientar testagem das parcerias e iniciar tratamento nelas quando houver resultado positivo ou surgimento de sintomas compatíveis.",
            "WRONG": "Orientar observação das parcerias assintomáticas e recomendar avaliação se aparecerem sintomas ou houver nova exposição sexual desprotegida.",
        },
        "complication": {
            "BEST": "Avaliar imediatamente doença inflamatória pélvica, epididimite e outros diagnósticos urgentes, ajustando tratamento e encaminhamento conforme gravidade.",
            "SUBOPTIMAL": "Ampliar exame físico e avaliação de gravidade antes de decidir necessidade de tratamento adicional, imagem ou encaminhamento especializado.",
            "PLAUSIBLE": "Ampliar cobertura antimicrobiana para complicação por clamídia e programar reavaliação em 24 horas se o paciente permanecer estável.",
            "WRONG": "Manter o esquema para clamídia, acrescentar analgesia e aguardar exames complementares antes de modificar o nível de cuidado.",
        },
    },
}
