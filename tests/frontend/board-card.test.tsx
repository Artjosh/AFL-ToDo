/**
 * Teste de componente: BoardCard (card do board Kanban).
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import BoardCard from "@/components/board-card";
import type { Task } from "@/lib/types";

const task: Task = {
  id: 7,
  titulo: "Estudar testes",
  descricao: "vitest + playwright",
  status: "pendente",
  position: 0,
  project_id: null,
  data_criacao: "2026-05-29T12:00:00Z",
  updated_at: "2026-05-29T12:00:00Z",
  creator: { id: 1, email: "ana@test.com" },
  assignees: [
    { id: 2, email: "bruno@test.com" },
    { id: 3, email: "carla@test.com" },
  ],
};

describe("BoardCard", () => {
  it("renderiza título, descrição e id", () => {
    render(<BoardCard task={task} />);
    expect(screen.getByText("Estudar testes")).toBeInTheDocument();
    expect(screen.getByText("vitest + playwright")).toBeInTheDocument();
    expect(screen.getByText("#7")).toBeInTheDocument();
  });

  it("mostra avatar do criador (sempre) e dos atribuídos", () => {
    render(<BoardCard task={task} />);
    // criador ana@test.com -> AN (sempre presente, mesmo sem atribuídos)
    expect(screen.getByText("AN")).toBeInTheDocument();
    // atribuídos: BR de bruno, CA de carla
    expect(screen.getByText("BR")).toBeInTheDocument();
    expect(screen.getByText("CA")).toBeInTheDocument();
  });

  it("mostra o criador mesmo sem nenhum atribuído", () => {
    const semAssignees: Task = { ...task, assignees: [] };
    render(<BoardCard task={semAssignees} />);
    expect(screen.getByText("AN")).toBeInTheDocument();
  });

  it("não duplica o avatar quando o criador também é atribuído", () => {
    const criadorAtribuido: Task = {
      ...task,
      assignees: [{ id: 1, email: "ana@test.com" }, { id: 2, email: "bruno@test.com" }],
    };
    render(<BoardCard task={criadorAtribuido} />);
    // "AN" aparece uma única vez (criador), não duplicado pelo assignee
    expect(screen.getAllByText("AN")).toHaveLength(1);
    expect(screen.getByText("BR")).toBeInTheDocument();
  });

  it("chama onClick ao clicar", () => {
    const onClick = vi.fn();
    render(<BoardCard task={task} onClick={onClick} />);
    fireEvent.click(screen.getByTestId("card-7"));
    expect(onClick).toHaveBeenCalledWith(task);
  });

  it("dispara onDragStart ao arrastar", () => {
    const onDragStart = vi.fn();
    render(<BoardCard task={task} onDragStart={onDragStart} />);
    const card = screen.getByTestId("card-7");
    fireEvent.dragStart(card, {
      dataTransfer: { setData: vi.fn(), effectAllowed: "" },
    });
    expect(onDragStart).toHaveBeenCalledWith(task);
  });
});
