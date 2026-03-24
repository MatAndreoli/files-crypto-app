# Relatório Final de Projeto: Cripto & Estego Pro

## 1. Informações Gerais
**Data:** 24 de março de 2026  
**Membros da Equipe:** Matheus Andreoli e Gabriel Araújo  
**Objetivo do Sistema:** Criptologia prática em formato visual englobando algoritmos vitais (Simétrica, Assimétrica e Esteganografia), com métricas baseadas em tempo e histórico auditável que comprovam a viabilidade dos modelos de ofuscação ensinados em aula.

---

## 2. Funcionalidades da Aplicação

A aplicação possui uma interface gráfica desenvolvida com *CustomTkinter* e baseia-se em quatro módulos principais:

1. **Criptografia Simétrica (AES-256):** 
   Utiliza a cifra AES nos modos de operação CBC e GCM. O modo GCM oferece confidencialidade e autenticação para os dados, alertando se houver alteração no arquivo. A chave criptográfica utilizada é gerada a partir da senha do usuário pelo algoritmo PBKDF2-HMAC-SHA256 (com 100.000 iterações), oferecendo proteção adicional contra ataques de força bruta.

2. **Criptografia Assimétrica Híbrida (RSA-2048 + AES-256):**
   Devido à lentidão do método RSA convencional para arquivos grandes (causada pela matemática assintótica), o sistema emprega o Envelopamento Digital:
   *   O arquivo real é criptografado rapidamente usando uma nova chave AES-256 gerada de forma automatizada (chave efêmera).
   *   O algoritmo RSA (Chave Pública/Privada) usa sua segurança apenas para criptografar e trancar essa chave AES de tamanho reduzido. Isso garante eficiência no processamento de arquivos maiores e torna escalonável a troca das chaves entre os usuários.

3. **Esteganografia (Técnica LSB):**
   Módulo que manipula matrizes através do pacote NumPy para ocultar dados dentro de imagens (PNG). A técnica LSB ("Least Significant Bit") funciona alterando apenas o último e menos importante bit numérico de cor dos pixels da foto verdadeira. Com isso, torna-se possível esconder mensagens ou até arquivos inteiros anexados sem deixar nenhuma distorção perceptível ao olho humano.

4. **Trilha de Dados, Logs e Auditoria:**
   A cada vez que uma funcionalidade é invocada pela interface gráfica, um registro estruturado é gravado automaticamente no banco de dados local SQLite (`operations.db`). Todos agrupam a data e horário oficial, descrição da ação usada, qual foi o arquivo alvo e o tempo de conclusão da operação em segundos para fins de auditorias. Esses mesmos dados moldam uma visualização dinâmica nativa dentro app.

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

### Análise sobre os Tempos e o Desempenho dos Algoritmos:

*   **Eficiência da Criptografia Simétrica (AES):** O tempo de processamento em ambos os modos AES apresentou rápido retorno por ser fundamentalmente simétrico. A operação de cifra consumiu apenas cerca de **2.7 segundos para um arquivo de 500 MB** fazendo uso da modalidade CBC. Já no método GCM houve aumento mínimo de custo atrelado ao registro obrigatório do seu bloco MAC, justificável pelo ganho adicional em autenticidade.
*   **Resultados da Estruturação Híbrida (RSA):** Ao criptografar os maiores valores listados (500 MB), o sistema precisou de somente **6.5 segundos**. Caso este arquivo tentasse ser criptografado na sua completude via algoritmo RSA primário, todo o sistema apresentaria alta oneração por limitação de software. Essa marca baixa de tempo, portanto, valida estruturalmente o método de envelopamento de trocas de chave.
*   **Alto Custo de Operação da Esteganografia (LSB):** Em contrapartida funcional, a tarefa para esconder os dados num espaço de imagem da memória demonstrou um tributo severo de uso da CPU (computador local). O ato de incorporar meros **50 MB em uma imagem consumiu cerca de 20 segundos**, que marca um coeficiente massivo de exigência frente aos testes combinados em AES e RSA. Devido a esse processamento oneroso e uso da RAM, a aplicação previne ativamente a injeção esteganográfica em massa para arquivos muito extensos, definindo os mesmos como limites evitáveis.

---

## 4. Amostra de Logs da Interface (Auditoria)

O aplicativo manteve e documentou com êxito os registros nos bancos de dados internos e relatórios exportados do aplicativo. O trecho delimitado a seguir resume as capturas e dados coletados das principais sessões do sistema avaliadas durante a submissão dos testes.

*(Nota: O ambiente foi alimentado por diferentes tamanhos massivos estáticos que flutuaram de `test_10MB.bin` a `test_500MB.bin`. Devido à quantidade gerada de logísticas intermediárias durante o mapeamento de teste prático, apenas uma seleção parcial representativa foi incluída nos códigos abaixo nestes cenários).*

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
