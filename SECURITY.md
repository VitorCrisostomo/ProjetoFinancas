# Cuidados com dados e credenciais

Não versione credenciais, tokens, chaves, bases locais, backups ou dados financeiros e pessoais reais. Exemplos e testes devem usar dados fictícios; não copie dados pessoais para fixtures, documentação ou capturas de tela.

Mantenha chaves, arquivos `.env` reais e backups fora do Git. Use `.env.example` somente com campos vazios ou placeholders. O `.gitignore` ajuda a prevenir novos arquivos, mas não remove arquivos já versionados nem dados do histórico.

Antes de publicar alterações, execute `gitleaks git . --redact --log-opts="--all"` para verificar todas as referências sem exibir valores sensíveis no relatório. A configuração mantém as regras padrão e permite somente duas senhas fictícias no arquivo de teste de autenticação; não exclua diretórios inteiros da verificação.

Se uma credencial for exposta, revogue-a ou rotacione-a no serviço responsável. Remover o conteúdo e limpar o histórico não invalida a credencial.

Após uma limpeza de histórico, atualize os clones e coordene a substituição de clones antigos. Não publique commits, branches ou tags antigas que possam reintroduzir os dados removidos; essas cópias ainda podem conter conteúdo sensível. Caches e commits antigos acessíveis pelo GitHub podem exigir uma solicitação ao suporte, conforme a [documentação de remoção de dados sensíveis](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository).
