// SPDX-License-Identifier: MIT
// AGENT-084 trigger: tx.origin used as an authentication check.
pragma solidity ^0.8.0;

contract TxOriginAuth {
    address public owner;

    function withdraw(uint256 amount) public {
        require(tx.origin == owner, "not the owner");
        payable(msg.sender).transfer(amount);
    }
}
