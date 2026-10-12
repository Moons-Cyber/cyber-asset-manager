# Relatório de Testes e Validação de Software - Sprint 3 (S3_07)

## 1. Casos de Teste Elaborados
Foram desenvolvidas duas suítes de testes automatizados utilizando os frameworks `pytest` e `unittest`.

### A. Módulo `GerenciadorAtivos` (`tests/test_gerenciador_ativos.py`)
- `test_lista_vazia_quando_arquivo_nao_existe`: Valida comportamento inicial sem base JSON.
- `test_cadastrar_e_buscar_ativo`: Testa fluxo positivo de inserção e consulta.
- `test_impede_ids_duplicados`: Valida se o sistema bloqueia ativos com IDs repetidos (`ValueError`).
- `test_busca_id_inexistente`: Retorna `None` para buscas com IDs inexistentes.
- `test_atualiza_e_persiste_dados`: Garante atualização de campos e persistência em arquivo.
- `test_atualizacao_de_id_inexistente`: Valida falha graciosa ao atualizar ID inexistente.
- `test_atualizacao_sem_campos_e_rejeitada`: Impede chamadas de atualização sem argumentos.
- `test_rejeita_campo_nao_permitido`: Valida restrição de atributos permitidos no contrato.
- `test_rejeita_vulnerabilidades_invalidas`: Garante tipagem dos objetos de vulnerabilidade (`TypeError`).
- `test_rejeita_vulnerabilidades_que_nao_sao_lista`: Rejeita estruturas que não sejam listas.
- `test_remove_ativo` e `test_remocao_de_id_inexistente`: Valida a remoção com sucesso e tratamento para ID inexistente.

### B. Módulo `Persistencia` (`tests/test_persistencia_unittest.py`)
- `test_salvar_e_carregar_reconstroi_objetos`: Garante que objetos serializados em JSON recuperam a classe correta na desserialização.
- `test_json_contem_uma_lista_de_objetos`: Valida se a estrutura gerada é um array JSON.
- `test_salvar_e_carregar_lista_vazia`: Garante resiliência no manuseio de coleções vazias.

---

## 2. Relatório de Cobertura (Coverage Report)

| Módulo | Cobertura |
| :--- | :--- |
| `src/persistencia/persistencia.py` | **100%** |
| `src/servicos/gerenciador_ativos.py` | **100%** |
| `src/modelos/vulnerabilidades.py` | **90%** |
| `src/modelos/notebook.py` | **86%** |
| `src/modelos/ativo.py` | **62%** |
| `src/modelos/roteador.py` | **43%** |
| `src/modelos/servidor.py` | **43%** |
| **TOTAL PROJETO** | **89%** |

---

## 3. Descrição de Defeitos e Correções Realizadas
- **Validação de Vulnerabilidades no `GerenciadorAtivos`**: Identificou-se a necessidade de impedir que strings soltas ou tipos arbitrários fossem inseridos na lista de vulnerabilidades. Foi adicionada a verificação explícita com `isinstance` e exceção do tipo `TypeError`, validada no teste `test_rejeita_vulnerabilidades_que_nao_sao_lista`.
- **Isolamento dos Arquivos nos Testes**: Evitou-se a poluição do ambiente de desenvolvimento através da utilização da fixture `tmp_path` do `pytest` e do módulo `tempfile` no `unittest`.