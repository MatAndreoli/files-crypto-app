# Relatório Final de Projeto: Cripto & Estego Pro

## 1. Informações Gerais
**Data:** 24 de março de 2026  
**Membros da Equipe:** Matheus Andreoli e equipe (Até 3 integrantes)  
**Objetivo do Sistema:** Criptologia prática em formato visual englobando algoritmos vitais (Simétrica, Assimétrica e Esteganografia), com métricas baseadas em tempo e histórico auditável que comprovam a viabilidade dos modelos de ofuscação ensinados em aula.

---

## 2. Descrição Detalhada da Aplicação (Funcionalidade)

O aplicativo utiliza a interface *CustomTkinter* para guiar os processamentos que ocorrem silenciosamente por baixo dos panos na camada do Python. As 4 molas mestras do software são:

1. **Camada de Criptografia Simétrica (AES-256):** 
   Utiliza a cifra AES em dois modos de operação modernos (CBC e GCM). O método GCM, particularmente, brilha por garantir confidencialidade e também verificação de autenticidade no mesmo pulso, evitando manipulações no arquivo em trânsito. A chave-mestre responsável por decifrar os arquivos é gerada de uma senha inserida usando 100.000 iterações de salt pelo algoritmo PBKDF2-HMAC-SHA256, resistindo massivamente a ataques de força bruta.

2. **Criptografia Assimétrica Híbrida (RSA-2048 + AES-256):**
   Criptografar arquivos arbitrários puros aplicando somente a fórmula RSA causaria extrema ineficiência ou corrupção por limitações da matemática de fatoração. Para transpor essa ineficiência, a aplicação resolve o processo através da técnica de "Envelopamento Digital" (Híbrida):
   *   O ficheiro é encriptado velozmente por uma nova chave AES-256 recém gerada só para ele (chamada *chave efêmera*).
   *   A poderosa criptografia RSA (Chave Pública/Privada) usa seu cadeado **única e exclusivamente na pequenina chave AES**, não no arquivo inteiro. Isto viabiliza a remessa pela web mantendo a total integridade de arquivos colossais.

3. **Esteganografia através de Substituição (Técnica LSB):**
   Módulo analítico em NumPy que se infiltra dentro de imagens do tipo PNG. A mágica da técnica "Least Significant Bit" na aplicação mascara as conversas ou os *binários (arquivos anexos inteiros)* alterando minimamente apenas o 1º bit visual do canal Alpha ou Colorido RGB das matrizes. Como resultado, o "hospedeiro" muda matematicamente de cor, mas o espectro visível para o olho humano se mantém invariável, garantindo excelente ofuscação (Security by Obscurity).

4. **Trilha de Históricos e Logs Interceptativos:**
   Através de *decorators* da linguagem (`@timed_operation`), qualquer instrução demandada por cliques na interface é interceptada por um log silencioso em plano de fundo no banco de dados incorporado SQLite (`operations.db`). Todos os registros guardam **horário de uso, arquivo demandado, ação escolhida e segundos exatos processados**, acessíveis nativamente pela aba de logs do aplicativo para a geração do relatório.

---

## 3. Análise de Performance e Desempenho (Tabela Lógica)

Abaixo encontra-se a consolidação dos tempos do log real provido pelo avaliador, baseando-se no Benchmark executado para **10 MB a 500 MB** avaliando as forças de AES, RSA e LSB:

| Carga Útil (MB) | Módulo (Ação) | AES-256-CBC | AES-256-GCM | RSA-Híbrido | Esteganografia LSB |
|-----------------|-------------------------|-------------|-------------|-------------|--------------------|
| **10 MB**       | *Cifrar / Ocultar*     | 0.054s      | 0.068s      | 0.050s      | 4.200s            |
| **10 MB**       | *Decifrar / Extrair*   | 0.046s      | 0.065s      | 0.063s      | 0.708s            |
| **25 MB**       | *Cifrar / Ocultar*     | 0.156s      | 0.181s      | 0.177s      | 10.691s           |
| **25 MB**       | *Decifrar / Extrair*   | 0.125s      | 0.180s      | 0.166s      | 1.465s            |
| **50 MB**       | *Cifrar / Ocultar*     | 0.271s      | 0.337s      | 0.276s      | 20.531s           |
| **50 MB**       | *Decifrar / Extrair*   | 0.203s      | 0.338s      | 0.332s      | 3.156s            |
| **100 MB**      | *Cifrar / Ocultar*     | 0.538s      | 0.679s      | 0.601s      | *(Limite evitado)*|
| **100 MB**      | *Decifrar / Extrair*   | 0.426s      | 0.651s      | 0.625s      | *(Limite evitado)*|
| **250 MB**      | *Cifrar / Ocultar*     | 1.297s      | 1.547s      | 5.126s      | *(Limite evitado)*|
| **250 MB**      | *Decifrar / Extrair*   | 1.169s      | 1.460s      | 1.533s      | *(Limite evitado)*|
| **500 MB**      | *Cifrar / Ocultar*     | 2.741s      | 3.454s      | 6.532s      | *(Limite evitado)*|
| **500 MB**      | *Decifrar / Extrair*   | 2.231s      | 7.703s      | 3.117s      | *(Limite evitado)*|

### Considerações e Análise (Desempenho dos Algoritmos):

*   **A Soberania da Cifragem Simétrica (AES):** A perfomance computacional em ambos os AES foi incrivelmente veloz. A cifra é extremamente otimizada, consumindo ínfimos **~2.7 segundos para travar estupendos 500 Megabytes inteiros** através de modo CBC. A variante GCM possui um custo de processamento muito pequeno associado à necessidade analítica do bloco MAC (verificação de adulteração), provando excelente custo benefício.
*   **O "Falso Peso" Híbrido (RSA):** Ao criptografar colossais 500MB, o sistema exigiu meros **6.5 segundos**. Caso a implementação se escorasse no algoritmo de RSA primário puro (trazendo o custo astronômico da força bruta do bloco matemático), o limite explodiria a taxa de falha. Este tempo só se manteve excelente em consequência ao método híbrido de trocas das chaves.
*   **A Carga e o Pedágio Vetorial (Esteganografia LSB):** Em nítido contraste, ocultar dados dentro da imagem vetorial LSB obriga o computador a pagar um tributo de memória RAM avassalador. Embargar **meramente 50 MB puxou brutais 20 segundos**, sendo o correspondente a mais de 35 vezes o esforço criptográfico do AES e RSA combinados na marca análoga. Por este motivo de carga irresponsável sobre os limites de banda e processamento, as cargas gigantescas são cortadas estrategicamente.

---

## 4. Histórico de Telemetria Auditável (Amostra de Logs Brutos)

O aplicativo manteve e documentou perfeitamente todo o extrato de dados das execuções em seu banco de dados e nos arquivos do servidor (via exportação permitida *csv/txt*). O excerto mais importante dos tempos oficiais do simulado de grande porte realizado nesta versão reflete o histórico das coletas da auditoria. 

*(Obs: Os arquivos inteiros manipulados para gerar essa carga variam entre tamanhos brutos de teste (`test_10MB.bin`, chegando até massas de `test_500MB.bin`). Foram omitidos os blocos intermediários nesta reprodução de relatório devido ao amplo volume emitido pelo software).*

```log
[2026-03-22 17:33:36.650] Benchmark Decrypt (RSA-2048 Híbrido) - Status: success - Tempo: 3.117075s
     Infos: Decifrado com sucesso. Tamanho restaurado: 524288000 bytes.

[2026-03-22 17:33:33.389] Benchmark Encrypt (RSA-2048 Híbrido) - Status: success - Tempo: 6.532254s
     Infos: Cifrado com criptografia híbrida. Tamanho original: 524288000 bytes.

[2026-03-22 17:33:21.819] Benchmark Decrypt (AES-256-GCM) - Status: success - Tempo: 7.703128s
     Infos: Decifrado e autenticado com sucesso. Tamanho restaurado: 524288000 bytes.

[2026-03-22 17:32:51.203] Benchmark Ocultar (Estego-LSB) - Status: success - Tempo: 20.531978s
     Infos: Arquivo 'test_50MB.bin' (52428800 bytes) ocultado com sucesso na imagem.

[2026-03-22 17:32:29.159] Benchmark Encrypt (AES-256-GCM) - Status: success - Tempo: 0.337692s
     Infos: Cifrado com autenticação GCM. Tamanho original: 52428800 bytes.

... FIM DO EXCERTO DE AUDITORIA ...
```
