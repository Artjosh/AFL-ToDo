# Projetos, board Kanban e colaboração

[← Voltar ao índice](../README.md)

A aplicação tem uma interface estilo **Trello/Jira**: um **board Kanban** com três
colunas (Pendente / Em andamento / Concluída) e **drag-and-drop** dos cards entre
elas. Suporta **projetos** (agrupando tarefas) e **compartilhamento** entre usuários.

## Board Kanban

- Cada tarefa é um card arrastável. Mover o card entre colunas altera o `status`;
  reordenar dentro/entre colunas ajusta a `position`. Ambos são persistidos via
  `POST /tasks/reorder` (com atualização otimista na UI e um indicador discreto de
  "Sincronizando...", sem recarregar a tela inteira).
- O botão `+` no topo de cada coluna cria uma tarefa já naquele status.
- Clicar num card abre o **detalhe** (título, descrição, status, pessoas e exclusão).
- **Avatares no card:** o **criador** aparece sempre (com um anel de destaque) e,
  ao lado, as **pessoas atribuídas**. Vale para tarefas soltas e de projeto — então
  você sempre vê sua miniatura nas suas tarefas. Se o criador também for atribuído,
  não há duplicação.

## Projetos (board aninhado)

- Um **projeto** agrupa tarefas. Na visão principal ele aparece como um **card
  especial**, posicionado **na coluna do seu próprio status** (Pendente / Em
  andamento / Concluída).
- O card do projeto é **arrastável entre as colunas** para mudar o status do
  projeto — respeitando a permissão (ver abaixo). Também dá para mudar pelo
  seletor de status dentro do board do projeto.
- Clicar no card do projeto **expande** o board daquele projeto, com as tarefas
  aninhadas — onde é possível criar, mover e editar tarefas do projeto.
- Tarefas "soltas" (sem projeto) vivem no board principal; tarefas de projeto
  vivem no board do projeto.

## Compartilhamento (membros e atribuídos)

Dois níveis de colaboração:

1. **Membros do projeto** — o dono adiciona pessoas por email (botão "Membros" na
   visão do projeto). Membros passam a **ver e editar** todas as tarefas do projeto.
2. **Atribuídos da tarefa** — qualquer pessoa com acesso à tarefa pode atribuir
   outros usuários a ela (no detalhe da tarefa). Os atribuídos aparecem como
   **avatares** no card e **ganham acesso àquela tarefa específica** — inclusive em
   **tarefas soltas** (fora de projeto). É o jeito de compartilhar uma tarefa
   avulsa: atribua alguém e ela passa a ver/editar aquele card no board dela.

> Para ser convidado, o usuário precisa **já ter acessado ao menos uma vez** (ter
> um registro no banco). Isso é uma decisão de simplicidade: não há convite por
> email para contas inexistentes.

## Permissões por membro (configuráveis pelo dono)

Ao abrir **Membros** no board do projeto, o dono configura, **por membro**, quatro
permissões independentes (caixas de seleção):

| Permissão | O que libera |
|-----------|--------------|
| **Mover o projeto** | trocar o status do **próprio projeto** (Pendente/Em andamento/Concluída) |
| **Mover tarefas** | arrastar as tarefas do projeto entre colunas (muda o status) |
| **Gerenciar tarefas** | criar, editar e excluir tarefas do projeto |
| **Receber alertas** | receber **email** quando uma tarefa é criada ou muda de status |

Padrões ao adicionar um membro: **mover tarefas** e **gerenciar tarefas** ligados;
**mover o projeto** e **receber alertas** desligados. O **dono** sempre pode tudo.
A UI reflete a permissão (sem "Mover tarefas" os cards nem ficam arrastáveis; sem
"Gerenciar tarefas" o botão "+ Nova tarefa" some) e o **backend revalida** cada
ação — a UI é só conveniência.

## Status do projeto

O projeto também é um "card" com **status próprio** (Pendente / Em andamento /
Concluída). Quem pode alterá-lo: o **dono** e os membros com **Mover o projeto**.
Os demais veem o status como um selo (somente leitura).

## Política ao remover um membro

Nas **configurações do projeto** (no modal de Membros, visível ao dono), define-se
o que acontece com as tarefas **criadas por um membro** quando ele é removido:

- **Revogar acesso** (padrão): o membro perde o acesso; as tarefas que ele criou no
  projeto são **transferidas para o dono** (não ficam órfãs) e as atribuições dele
  no projeto são removidas.
- **Mantém como dono**: o membro **continua criador** das tarefas que fez e segue
  podendo vê-las, mesmo sem ser mais membro do projeto.

## Alertas por email (backend Python)

Quando uma tarefa de um projeto é **criada** ou tem o **status alterado**, o backend
envia um **email de alerta** (via SMTP/Brevo) para os destinatários configurados:
o **dono** (se "Eu recebo alertas" estiver ligado nas configurações) e cada membro
com **Receber alertas** ligado. Quem **originou** a ação não recebe alerta da
própria mudança. O envio é assíncrono (fire-and-forget) e nunca atrasa/derruba a
ação. Sem SMTP configurado (dev), é um no-op silencioso.

## Modelo de acesso (importante)

O acesso deixou de ser apenas *ownership* e passou a ser *membership*. Um usuário
pode ver/editar uma tarefa se for:
- o **criador** da tarefa;
- um **atribuído** da tarefa; ou
- **membro do projeto** ao qual a tarefa pertence.

Regras adicionais:
- Só o **dono do projeto** pode adicionar/remover membros, configurar permissões,
  alterar nome/descrição/políticas e excluir o projeto.
- Ações de tarefa (mover, criar/editar/excluir) e mover o projeto respeitam as
  **permissões por membro** descritas acima.
- Remover um membro segue a **política de remoção** do projeto (revogar/manter).
- O backend nunca confia em ids do frontend — o usuário vem sempre do token, e a
  regra de acesso é centralizada em `app/api/access.py`.

## Endpoints relacionados

Ver [Endpoints](./11-endpoints.md) para a lista completa (projetos, membros,
assignees e tarefas com filtros `?project_id=` e `?standalone=`).
