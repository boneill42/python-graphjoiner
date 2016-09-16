from datetime import datetime

from attr import attrs, attrib
from graphql import graphql, GraphQLSchema, GraphQLInt, GraphQLString, GraphQLArgument

from graphjoiner import single, many, JoinType, RootJoinType, field
from .execution_test_cases import ExecutionTestCases


@attrs
class Book(object):
    id = attrib()
    title = attrib()
    author_id = attrib()


@attrs
class Author(object):
    id = attrib()
    name = attrib()


all_authors = [
    Author(1, "PG Wodehouse"),
    Author(2, "Joseph Heller"),
]

all_books = [
    Book(id=1, title="Leave It to Psmith", author_id=1),
    Book(id=2, title="Right Ho, Jeeves", author_id=1),
    Book(id=3, title="Catch-22", author_id=2),
]


class ObjJoinType(JoinType):
    def fetch_immediates(self, request, objs):
        requested_fields = [
            (field, self.fields()[field].attr)
            for field in request.requested_fields
        ]
        
        def read_obj(obj):
            return dict((key, getattr(obj, attr)) for (key, attr) in requested_fields)
        
        return list(map(read_obj, objs))


class AuthorJoinType(ObjJoinType):
    @staticmethod
    def fields():
        return {
            "id": field(attr="id", type=GraphQLInt),
            "name": field(attr="name", type=GraphQLString),
            "books": many(
                BookJoinType,
                lambda *_: all_books,
                join={"id": "authorId"},
            ),
        }


class BookJoinType(ObjJoinType):
    @staticmethod
    def fields():
        return {
            "id": field(attr="id", type=GraphQLInt),
            "title": field(attr="title", type=GraphQLString),
            "authorId": field(attr="author_id", type=GraphQLInt),
            "author": single(
                AuthorJoinType,
                lambda *_: all_authors,
                join={"authorId": "id"},
            ),
        }


class Root(RootJoinType):
    @classmethod
    def fields(cls):
        return {
            "books": many(BookJoinType, lambda *_: all_books),
            "author": single(AuthorJoinType, cls._author_query, args={"id": GraphQLArgument(type=GraphQLInt)}),
        }
    
    @classmethod
    def _author_query(cls, request, _):
        authors = all_authors
        
        author_id = request.args.get("id")
        if author_id is not None:
            authors = list(filter(lambda author: author.id == int(author_id), authors))
        
        return authors


class TestGraphJoiner(ExecutionTestCases):
    def execute(self, query):
        schema = GraphQLSchema(
            query=Root().to_graphql_type(),
        )
        
        result = graphql(schema, query)
        
        assert not result.errors
        return result.data