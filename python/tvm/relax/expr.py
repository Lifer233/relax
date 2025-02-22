# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
# pylint: disable=invalid-name, unused-import, super-init-not-called
# pylint: disable=redefined-builtin
"""The expression nodes of Relax."""
from typing import Any, List, Optional, Union
import typing

import tvm
import tvm._ffi

from .. import relay
from ..ir import BaseFunc, Node, SourceName, Span
from ..relay import Id, Tuple, TupleGetItem
from ..runtime import String
from ..tir import PrimExpr
from . import _ffi_api, ty

# It is a workaround for mypy: https://github.com/python/mypy/issues/7866#issuecomment-549454370
# This feature is not supported until python 3.10:
# https://docs.python.org/3.10/whatsnew/3.10.html#pep-613-typealias
Expr = Union[relay.Expr]
Type = Union[relay.Type]
GlobalVar = Union[relay.GlobalVar]
Call = Union[relay.Call]
If = Union[relay.If]
const = Union[relay.const]
Constant = Union[relay.Constant]


@tvm._ffi.register_object("relax.expr.ShapeExpr")
class ShapeExpr(Expr):
    """A shape expression which allows users to construct a shape containing PrimExpr."""

    values: List[PrimExpr]

    def __init__(
        self,
        values: Union[List[PrimExpr], typing.Tuple[PrimExpr, ...], tvm.ir.Array],
        span: Span = None,
    ) -> None:
        self.__init_handle_by_constructor__(_ffi_api.ShapeExpr, values, span)  # type: ignore

    def __getitem__(self, index):
        if index >= len(self):
            raise IndexError("Tuple index out of range")
        return self.values[index]

    def __len__(self):
        return len(self.values)


def make_shape(shape: Union[List[Any], typing.Tuple[Any, ...]]) -> ShapeExpr:
    if isinstance(shape, (list, tuple)):
        return ShapeExpr(shape)
    raise ValueError("Wrong type")


@tvm._ffi.register_object("relax.expr.RuntimeDepShape")
class RuntimeDepShape(Expr):
    """A shape expression which allows users to construct a runtime dependent shape."""

    def __init__(self, span: Span = None) -> None:
        self.__init_handle_by_constructor__(_ffi_api.RuntimeDepShape, span)  # type: ignore


@tvm._ffi.register_object("relax.expr.Var")
class Var(Expr):
    """The variable class for all Relax bindings."""

    vid: Id
    type_annotation: Optional[Type]

    def __init__(
        self,
        name_hint: str,
        shape_annotation: Optional[Union[List[Any], typing.Tuple[Any, ...]]] = None,
        type_annotation: Optional[Type] = None,
        span: Span = None,
    ) -> None:
        if isinstance(shape_annotation, (list, tuple)):
            shape_annotation = make_shape(shape_annotation)
        self.__init_handle_by_constructor__(
            _ffi_api.Var if isinstance(name_hint, str) else _ffi_api.VarFromId,  # type: ignore
            name_hint,
            shape_annotation,
            type_annotation,
            span,
        )

    @property
    def name_hint(self):
        """Get name hint of the current var."""
        name = str(self.vid.name_hint)
        return name

    def __call__(self, *args: Any, attrs=None) -> Call:
        if self.checked_type and isinstance(self.checked_type, ty.FuncType):
            return Call(self, args, attrs=attrs)
        else:
            raise TypeError("Only vars with function type can be called")


@tvm._ffi.register_object("relax.expr.DataflowVar")
class DataflowVar(Var):
    """A sub-type of the variable node used to mark dataflow variables from
    normal visible "function local" bindings."""

    def __init__(
        self,
        name_hint: Union[str, Id],
        shape_annotation: Optional[Union[List[Any], typing.Tuple[Any, ...]]] = None,
        type_annotation: Optional[Type] = None,
        span: Span = None,
    ) -> None:
        if isinstance(shape_annotation, (list, tuple)):
            shape_annotation = make_shape(shape_annotation)

        self.__init_handle_by_constructor__(
            _ffi_api.DataflowVar  # type: ignore
            if isinstance(name_hint, str)
            else _ffi_api.DataflowVarFromId,  # type: ignore
            name_hint,
            shape_annotation,
            type_annotation,
            span,
        )


@tvm._ffi.register_object("relax.expr.Binding")
class Binding(Node):
    """The base class of a binding in Relax."""

    ...


@tvm._ffi.register_object("relax.expr.MatchShape")
class MatchShape(Binding):
    """Symbolic shape match, binds the variable of the lhs with the rhs."""

    value: Expr
    pattern: List[PrimExpr]
    var: Var

    def __init__(self, value: Expr, pattern: List[PrimExpr], var: Var, span: Span = None) -> None:
        self.__init_handle_by_constructor__(
            _ffi_api.MatchShape, value, pattern, var, span  # type: ignore
        )


@tvm._ffi.register_object("relax.expr.VarBinding")
class VarBinding(Binding):
    """Variable binding, bind he variable of the lhs with the rhs."""

    var: Var
    value: Expr

    def __init__(self, var: Var, value: Expr, span: Span = None) -> None:
        self.__init_handle_by_constructor__(_ffi_api.VarBinding, var, value, span)  # type: ignore


@tvm._ffi.register_object("relax.expr.BindingBlock")
class BindingBlock(Node):
    """base class of binding block, bindings inside can be impure
    (with side effect or control flow)"""

    bindings: List[Binding]

    def __init__(self, bindings: List[Binding], span: Span = None) -> None:
        self.__init_handle_by_constructor__(_ffi_api.BindingBlock, bindings, span)  # type: ignore


@tvm._ffi.register_object("relax.expr.DataflowBlock")
class DataflowBlock(BindingBlock):
    """dataflow block, bindings inside are pure (no side effect and no control flow)"""

    def __init__(self, bindings: List[Binding], span: Span = None) -> None:
        self.__init_handle_by_constructor__(_ffi_api.DataflowBlock, bindings, span)  # type: ignore


@tvm._ffi.register_object("relax.expr.SeqExpr")
class SeqExpr(Expr):
    """A sequence of binding blocks followed by an expression."""

    blocks: List[BindingBlock]
    body: Expr

    def __init__(self, blocks: List[BindingBlock], body: Expr, span: Span = None) -> None:
        self.__init_handle_by_constructor__(_ffi_api.SeqExpr, blocks, body, span)  # type: ignore


@tvm._ffi.register_object("relax.expr.Function")
class Function(BaseFunc):
    """A Relax function."""

    params: List[Var]
    body: Expr
    ret_type: Type
    ret_shape: Expr
    attrs: Optional[tvm.ir.DictAttrs]

    def __init__(
        self,
        params: List[Var],
        body: Expr,
        ret_type: Type,
        ret_shape: Expr,
        attrs: Optional[tvm.ir.DictAttrs] = None,
        span: Optional[Span] = None,
    ) -> None:
        self.__init_handle_by_constructor__(
            _ffi_api.Function, params, body, ret_type, ret_shape, attrs, span  # type: ignore
        )

    @staticmethod
    def create_unchecked(
        params: List[Var],
        body: Expr,
        ret_type: Type,
        ret_shape: Expr,
        attrs: Optional[tvm.ir.DictAttrs] = None,
        span: Optional[Span] = None,
    ):
        """Construct a relax.Function but without type checking."""
        return _ffi_api.Function_CreateUnchecked(  # type: ignore
            params, body, ret_type, ret_shape, attrs, span
        )

    def __call__(self, *args):
        """Invoke the global function.

        Parameters
        ----------
        args: List[relax.Expr]
            Arguments.
        """
        return Call(self, args, None, None)

    def script(self, show_meta: bool = False) -> str:
        """Print relax.Function into TVMScript

        Parameters
        ----------
        show_meta : bool
            Whether to show meta information

        Returns
        -------
        script : str
            The TVM Script of the relax.Function
        """
        return tvm._ffi.get_global_func("script.AsRelaxScript")(self, show_meta)  # type: ignore

    def show(self, style: str = "light") -> None:
        """
        A sugar for print highlighted TVM script.

        Parameters
        ----------
        style : str, optional
            Pygments styles extended by "light" (default) and "dark", by default "light"
        """
        from tvm.script.highlight import cprint  # pylint: disable=import-outside-toplevel

        # Use deferred import to avoid circular import while keeping cprint under tvm/script
        cprint(self, style=style)


@tvm._ffi.register_object("relax.expr.ExternFunc")
class ExternFunc(BaseFunc):
    """extern function, which can represent a TIR PrimFunc or a PackedFunc."""

    global_symbol: String

    def __init__(self, global_symbol: String, span: Span = None) -> None:
        self.__init_handle_by_constructor__(
            _ffi_api.ExternFunc, global_symbol, span  # type: ignore
        )


def extern(name: str, span: Span = None):
    """Create extern function."""
    return ExternFunc(name, span)


def te_tensor(value: Expr, name: str = "rxplaceholder"):
    """Create te tensor from relax expression."""
    return _ffi_api.TETensor(value, name)  # type: ignore


def _update_type(expr: Expr, type: Type) -> None:
    _ffi_api.UpdateType(expr, type)  # type: ignore


def _update_shape(expr: Expr, shape: Optional[tvm.runtime.Object]) -> None:
    _ffi_api.UpdateShape(expr, shape)  # type: ignore
