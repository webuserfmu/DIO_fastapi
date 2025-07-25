from fastapi import FastAPI, Depends, HTTPException, status, Query, Path, Body
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float, DateTime, func, ForeignKey, select
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship, selectinload, Mapped
from typing import AsyncGenerator, List, Optional
from pydantic import BaseModel, UUID4, Field
from datetime import datetime
import uuid
import os

from sqlalchemy.exc import IntegrityError, DataError
from asyncpg.exceptions import StringDataRightTruncationError, UniqueViolationError, NotNullViolationError


DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL não definida. Exemplo: postgresql+asyncpg://user:password@host:port/dbname"
    )

engine = create_async_engine(DATABASE_URL, echo=True)

AsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)

Base = declarative_base()


class CategoriaIn(BaseModel):
    nome: str = Field(..., max_length=10, description="Nome da categoria (máximo 10 caracteres)")


class CategoriaOut(CategoriaIn):
    id: UUID4 = Field(..., description="ID único da categoria (UUID)")
    pk_id: int = Field(..., description="Chave primária interna da categoria")

    class Config:
        from_attributes = True


class CentroTreinamentoIn(BaseModel):
    nome: str = Field(..., max_length=50, description="Nome do Centro de Treinamento (máximo 50 caracteres)")
    endereco: str = Field(..., max_length=100, description="Endereço do Centro de Treinamento (máximo 100 caracteres)")
    proprietario: str = Field(..., max_length=50,
                              description="Nome do proprietário do Centro de Treinamento (máximo 50 caracteres)")


class CentroTreinamentoOut(CentroTreinamentoIn):
    id: UUID4 = Field(..., description="ID único do Centro de Treinamento (UUID)")
    pk_id: int = Field(..., description="Chave primária interna do Centro de Treinamento")

    class Config:
        from_attributes = True


class CategoriaNomeOut(BaseModel):
    nome: str = Field(..., description="Nome da categoria")

    class Config:
        from_attributes = True


class CentroTreinamentoNomeOut(BaseModel):
    nome: str = Field(..., description="Nome do Centro de Treinamento")

    class Config:
        from_attributes = True


class AtletaSimplificadoOut(BaseModel):
    id: UUID4 = Field(..., description="ID único do atleta (UUID)")
    created_at: datetime = Field(..., description="Data e hora de criação do registro do atleta")
    nome: str = Field(..., description="Nome do atleta")
    centro_treinamento: CentroTreinamentoNomeOut = Field(
        ...,
        description="Informações simplificadas do centro de treinamento do atleta"
    )
    categoria: CategoriaNomeOut = Field(..., description="Informações simplificadas da categoria do atleta")

    class Config:
        from_attributes = True


class AtletaIn(BaseModel):
    nome: str = Field(..., max_length=100, description="Nome do atleta (máximo 100 caracteres)")
    cpf: str = Field(
        ...,
        min_length=11,
        max_length=11,
        description="CPF do atleta (exatamente 11 dígitos)", pattern=r"^\d{11}$"
    )
    idade: int = Field(..., gt=0, description="Idade do atleta (deve ser maior que 0)")
    peso: float = Field(..., gt=0, description="Peso do atleta em kg (deve ser maior que 0)")
    altura: float = Field(..., gt=0, description="Altura do atleta em metros (deve ser maior que 0)")
    sexo: str = Field(..., min_length=1, max_length=1, pattern=r"^[MF]$", description="Sexo do atleta (M ou F)")
    centro_treinamento_pk_id: int = Field(..., description="ID da chave primária do Centro de Treinamento associado")
    categoria_pk_id: int = Field(..., description="ID da chave primária da Categoria associada")


class AtletaOut(BaseModel):
    id: UUID4 = Field(..., description="ID único do atleta (UUID)")
    pk_id: int = Field(..., description="Chave primária interna do atleta")
    nome: str = Field(..., description="Nome do atleta")
    cpf: str = Field(..., description="CPF do atleta")
    idade: int = Field(..., description="Idade do atleta")
    peso: float = Field(..., description="Peso do atleta")
    altura: float = Field(..., description="Altura do atleta")
    sexo: str = Field(..., description="Sexo do atleta")
    created_at: datetime = Field(..., description="Data e hora de criação do registro do atleta")
    categoria: CategoriaOut = Field(..., description="Informações da categoria do atleta")
    centro_treinamento: CentroTreinamentoOut = Field(..., description="Informações do centro de treinamento do atleta")

    class Config:
        from_attributes = True


class AtletaPaginatedOut(BaseModel):
    items: List[AtletaSimplificadoOut] = Field(..., description="Lista de atletas")
    total: int = Field(..., description="Número total de atletas que correspondem à query")
    limit: int = Field(..., description="O limite de registros aplicado à query")
    offset: int = Field(..., description="O offset (registros pulados) aplicado à query")


class AtletaUpdate(BaseModel):
    nome: Optional[str] = Field(None, description='Nome do atleta')
    cpf: Optional[str] = Field(None, description='CPF do atleta')
    idade: Optional[int] = Field(None, description='Idade do atleta')
    peso: Optional[float] = Field(None, description='Peso do atleta')
    altura: Optional[float] = Field(None, description='Altura do atleta')
    sexo: Optional[str] = Field(None, description='Sexo do atleta')
    categoria_id: Optional[UUID4] = Field(None, description='UUID da categoria associada')
    centro_treinamento_id: Optional[UUID4] = Field(None, description='UUID do centro de treinamento associado')


class Categoria(Base):
    __tablename__ = "categoria"
    pk_id = Column(Integer, primary_key=True, index=True)
    id = Column(PG_UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    nome = Column(String(10), unique=True, nullable=False)

    atletas: Mapped[List["Atleta"]] = relationship(
        back_populates="categoria", lazy='selectin'
    )


class CentroTreinamento(Base):
    __tablename__ = "centro_treinamento"
    pk_id = Column(Integer, primary_key=True, index=True)
    id = Column(PG_UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    nome = Column(String(50), unique=True, nullable=False)
    endereco = Column(String(100), nullable=False)
    proprietario = Column(String(50), nullable=False)

    atletas: Mapped[List["Atleta"]] = relationship(
        back_populates="centro_treinamento", lazy='selectin'
    )


class Atleta(Base):
    __tablename__ = "atleta"
    pk_id = Column(Integer, primary_key=True, index=True)
    id = Column(PG_UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    nome = Column(String(100), nullable=False)
    cpf = Column(String(11), unique=True, nullable=False)
    idade = Column(Integer, nullable=False)
    peso = Column(Float(precision=2), nullable=False)
    altura = Column(Float(precision=2), nullable=False)
    sexo = Column(String(1), nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())

    categoria_id: Mapped[int] = Column(ForeignKey("categoria.pk_id"), index=True, nullable=False)
    categoria: Mapped["Categoria"] = relationship(
        back_populates="atletas", lazy='selectin'
    )

    centro_treinamento_id: Mapped[int] = Column(ForeignKey("centro_treinamento.pk_id"), index=True, nullable=False)
    centro_treinamento: Mapped["CentroTreinamento"] = relationship(
        back_populates="atletas", lazy='selectin'
    )


async def create_db_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created/checked.")


app = FastAPI(
    title="API de Gerenciamento de Atletas",
    description="Uma API para gerenciar informações de atletas, categorias e centros de treinamento.",
    version="1.0.0"
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@app.on_event("startup")
async def startup_event():
    await create_db_tables()


@app.get("/", summary="Endpoint raiz da API", tags=["Geral"])
async def root():
    return {"message": "Bem-vindo à API de Gerenciamento de Atletas!"}


@app.get(
    "/categorias/",
    summary="Consultar todas as Categorias",
    status_code=status.HTTP_200_OK,
    response_model=list[CategoriaOut],
    tags=["Categorias"]
)
async def read_categorias(
    skip: int = Query(0, ge=0, description="Número de registros para pular"),
    limit: int = Query(10, ge=1, le=100, description="Número máximo de registros a retornar"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Categoria).offset(skip).limit(limit))
    categorias = result.scalars().all()
    return categorias


@app.get(
    "/categorias/{categoria_id}",
    summary="Consultar Categoria por ID",
    status_code=status.HTTP_200_OK,
    response_model=CategoriaOut,
    tags=["Categorias"]
)
async def get_categoria_by_id(
    categoria_id: UUID4 = Path(..., description="ID único da categoria (UUID)"),
    db: AsyncSession = Depends(get_db)
):
    query = select(Categoria).where(Categoria.id == categoria_id)
    result = await db.execute(query)
    categoria = result.scalars().first()

    if not categoria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Categoria não encontrada."
        )
    return categoria


@app.post(
    "/categorias/",
    response_model=CategoriaOut,
    status_code=status.HTTP_201_CREATED,
    summary="Criar uma nova Categoria",
    tags=["Categorias"]
)
async def create_categoria(
    body: CategoriaIn,
    db: AsyncSession = Depends(get_db)
):
    query = select(Categoria).where(Categoria.nome == body.nome)
    result = await db.execute(query)
    existing_categoria = result.scalars().first()

    if existing_categoria:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            detail=f"Categoria com nome '{body.nome}' já existe.",
            headers={"Location": f"/categorias/{existing_categoria.id}"}
        )

    db_categoria = Categoria(**body.model_dump())
    db.add(db_categoria)
    try:
        await db.commit()
        await db.refresh(db_categoria)
        return db_categoria
    except IntegrityError as e:
        if isinstance(e.orig, StringDataRightTruncationError):
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"O nome da categoria '{body.nome}' é muito longo. Máximo permitido: 10 caracteres."
            )
        elif isinstance(e.orig, UniqueViolationError):
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Conflito de dados: O nome da categoria '{body.nome}' já existe."
            )
        elif isinstance(e.orig, NotNullViolationError):
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Um campo obrigatório está faltando para a categoria."
            )
        else:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ocorreu um erro inesperado de integridade: {e.orig}"
            )
    except DataError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Erro de formato de dados: {e.orig}"
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro inesperado no servidor: {e}"
        )


@app.post(
    "/centros_treinamento/",
    response_model=CentroTreinamentoOut,
    status_code=status.HTTP_201_CREATED,
    summary="Criar um novo Centro de Treinamento",
    tags=["Centros de Treinamento"]
)
async def create_centro_treinamento(
    body: CentroTreinamentoIn,
    db: AsyncSession = Depends(get_db)
):
    query = select(CentroTreinamento).where(CentroTreinamento.nome == body.nome)
    result = await db.execute(query)
    existing_centro = result.scalars().first()

    if existing_centro:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            detail=f"Centro de treinamento com nome '{body.nome}' já existe.",
            headers={"Location": f"/centros_treinamento/{existing_centro.id}"}
        )

    db_centro = CentroTreinamento(**body.model_dump())
    db.add(db_centro)
    try:
        await db.commit()
        await db.refresh(db_centro)
        return db_centro
    except IntegrityError as e:
        if isinstance(e.orig, StringDataRightTruncationError):
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Um dos campos (nome, endereco, proprietario) é muito longo para o banco de dados."
            )
        elif isinstance(e.orig, UniqueViolationError):
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Conflito de dados: Centro de treinamento com nome '{body.nome}' já existe."
            )
        elif isinstance(e.orig, NotNullViolationError):
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Um campo obrigatório está faltando para o centro de treinamento."
            )
        else:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ocorreu um erro inesperado de integridade: {e.orig}"
            )
    except DataError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Erro de formato de dados: {e.orig}"
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro inesperado no servidor: {e}"
        )


@app.get(
    "/centros_treinamento/",
    summary="Consultar todos os Centros de Treinamento",
    status_code=status.HTTP_200_OK,
    response_model=List[CentroTreinamentoOut],
    tags=["Centros de Treinamento"]
)
async def read_centros_treinamento(
    skip: int = Query(0, ge=0, description="Número de registros para pular"),
    limit: int = Query(10, ge=1, le=100, description="Número máximo de registros a retornar"),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(CentroTreinamento).offset(skip).limit(limit))
    centros = result.scalars().all()
    return centros


@app.get(
    "/centros_treinamento/{centro_treinamento_id}",
    summary="Consultar Centro de Treinamento por ID",
    status_code=status.HTTP_200_OK,
    response_model=CentroTreinamentoOut,
    tags=["Centros de Treinamento"]
)
async def get_centro_treinamento_by_id(
    centro_treinamento_id: UUID4 = Path(..., description="ID único do centro de treinamento (UUID)"),
    db: AsyncSession = Depends(get_db)
):
    query = select(CentroTreinamento).where(CentroTreinamento.id == centro_treinamento_id)
    result = await db.execute(query)
    centro_treinamento = result.scalars().first()

    if not centro_treinamento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Centro de Treinamento não encontrado."
        )
    return centro_treinamento


@app.post(
    "/atletas/",
    response_model=AtletaOut,
    status_code=status.HTTP_201_CREATED,
    summary="Criar um novo Atleta",
    tags=["Atletas"]
)
async def create_atleta(
    body: AtletaIn,
    db: AsyncSession = Depends(get_db)
):
    result_cpf = await db.execute(select(Atleta).filter(Atleta.cpf == body.cpf))
    if result_cpf.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"CPF '{body.cpf}' já cadastrado.")

    result_categoria = await db.execute(select(Categoria).filter(Categoria.pk_id == body.categoria_pk_id))
    categoria = result_categoria.scalar_one_or_none()
    if not categoria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Categoria com pk_id {body.categoria_pk_id} não encontrada."
        )

    result_centro = await db.execute(select(CentroTreinamento).filter(
        CentroTreinamento.pk_id == body.centro_treinamento_pk_id)
    )
    centro_treinamento = result_centro.scalar_one_or_none()
    if not centro_treinamento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Centro de Treinamento com pk_id {body.centro_treinamento_pk_id} não encontrado."
        )

    db_atleta = Atleta(
        nome=body.nome,
        cpf=body.cpf,
        idade=body.idade,
        peso=body.peso,
        altura=body.altura,
        sexo=body.sexo,
        centro_treinamento_id=centro_treinamento.pk_id,
        categoria_id=categoria.pk_id
    )
    db.add(db_atleta)
    try:
        await db.commit()
        await db.refresh(db_atleta)
        return db_atleta
    except IntegrityError as e:
        if isinstance(e.orig, StringDataRightTruncationError):
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Um dos campos string (nome, cpf, sexo) é muito longo para a coluna no banco de dados."
            )
        elif isinstance(e.orig, UniqueViolationError):
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Conflito de dados: O CPF '{body.cpf}' já está cadastrado ou houve outro erro de unicidade."
            )
        elif isinstance(e.orig, NotNullViolationError):
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Um campo obrigatório está faltando para o atleta."
            )
        elif "foreign key" in str(e.orig).lower():
            await db.rollback()
            raise HTTPException(
                 status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                 detail="Erro de chave estrangeira: Categoria ou Centro de Treinamento não existe ou é inválido."
             )
        else:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ocorreu um erro inesperado de integridade: {e.orig}"
            )
    except DataError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Erro de formato de dados (ex: tipo incorreto para idade, peso, altura): {e.orig}"
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro inesperado no servidor: {e}"
        )


@app.patch(
    "/atletas/{id}",
    summary="Atualizar Atleta por UUID",
    status_code=status.HTTP_200_OK,
    response_model=AtletaOut,
    tags=["Atletas"]
)
async def update_atleta(
    id: UUID4 = Path(..., description="ID do atleta (UUID)"),
    atleta_update: AtletaUpdate = Body(...),
    db: AsyncSession = Depends(get_db)
):
    query = select(Atleta).where(Atleta.id == id)
    result = await db.execute(query)
    atleta_db = result.scalars().first()

    if not atleta_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Atleta não encontrado."
        )

    update_data = atleta_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(atleta_db, key, value)

    try:
        await db.commit()
        await db.refresh(atleta_db)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não foi possível atualizar o atleta devido a uma restrição de integridade."
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocorreu um erro inesperado ao atualizar o atleta: {e}"
        )

    return atleta_db


@app.delete(
    "/atletas/{id}",
    summary="Excluir Atleta por ID (UUID)",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Atletas"]
)
async def delete_atleta(
    id: UUID4 = Path(..., description="ID único do atleta (UUID)"),
    db: AsyncSession = Depends(get_db)
):
    query = select(Atleta).where(Atleta.id == id)
    result = await db.execute(query)
    atleta = result.scalars().first()

    if not atleta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Atleta não encontrado."
        )

    await db.delete(atleta)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não é possível excluir o atleta porque ele está vinculado a outras entidades."
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocorreu um erro inesperado ao excluir o atleta: {e}"
        )
    return None


@app.get(
    "/atletas/",
    summary="Consultar todos os Atletas",
    status_code=status.HTTP_200_OK,
    response_model=AtletaPaginatedOut,
    tags=["Atletas"]
)
async def read_atletas(
    nome: Optional[str] = Query(None, description="Filtrar atletas por nome exato"),
    cpf: Optional[str] = Query(None, description="Filtrar atletas por CPF exato"),
    skip: int = Query(0, ge=0, description="Número de registros para pular"),
    limit: int = Query(10, ge=1, le=100, description="Número máximo de registros a retornar"),
    db: AsyncSession = Depends(get_db)
):
    print(f"DEBUG: Requisição para /atletas/ - nome={nome}, cpf={cpf}, skip={skip}, limit={limit}")

    base_query = select(Atleta)

    if nome:
        base_query = base_query.where(Atleta.nome == nome)
        print(f"DEBUG: Filtro por nome aplicado. Query parcial: {base_query}")
    if cpf:
        base_query = base_query.where(Atleta.cpf == cpf)
        print(f"DEBUG: Filtro por CPF aplicado. Query parcial: {base_query}")

    count_query = select(func.count()).select_from(base_query.subquery())

    print(f"DEBUG: Consulta para total: {count_query}")
    total_result = await db.execute(count_query)
    total_atletas = total_result.scalar_one()
    print(f"DEBUG: Total de atletas filtrados: {total_atletas}")

    paginated_query = base_query.order_by(Atleta.pk_id).offset(skip).limit(limit)
    paginated_query = paginated_query.options(selectinload(Atleta.categoria), selectinload(Atleta.centro_treinamento))
    print(f"DEBUG: Consulta para itens: {paginated_query}")

    result = await db.execute(paginated_query)
    atletas_data = result.scalars().all()
    print(f"DEBUG: Número de itens retornados: {len(atletas_data)}")

    return AtletaPaginatedOut(
        items=atletas_data,
        total=total_atletas,
        limit=limit,
        offset=skip
    )


@app.get(
    "/atletas/{atleta_id}",
    summary="Consultar Atleta por ID",
    status_code=status.HTTP_200_OK,
    response_model=AtletaOut,
    tags=["Atletas"]
)
async def get_atleta_by_id(
    atleta_id: UUID4 = Path(..., description="ID único do atleta (UUID)"),
    db: AsyncSession = Depends(get_db)
):
    query = select(Atleta).where(Atleta.id == atleta_id).options(
        selectinload(Atleta.categoria),
        selectinload(Atleta.centro_treinamento)
    )
    result = await db.execute(query)
    atleta = result.scalars().first()

    if not atleta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Atleta não encontrado."
        )
    return atleta
