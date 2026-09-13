// SPDX-License-Identifier: MIT
// AGENT-083 trigger: delegatecall to a caller-supplied address.
pragma solidity ^0.8.0;

contract UnsafeDelegatecall {
    function forward(address target, bytes memory payload) public {
        (bool ok, ) = target.delegatecall(payload);
        require(ok, "delegatecall failed");
    }
}
