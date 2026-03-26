// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

interface IConditionalTokens {
    function splitPosition(address collateralToken, bytes32 parentCollectionId, bytes32 conditionId, uint[] calldata partition, uint amount) external;
    function mergePositions(address collateralToken, bytes32 parentCollectionId, bytes32 conditionId, uint[] calldata partition, uint amount) external;
}

contract PolymarketAutomator {
    IConditionalTokens public constant CTF = IConditionalTokens(0x4D97DCd97eC945f40cF65F87097ACe5EA0476045);
    address public constant USDC = 0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174; 
    address public owner;

    modifier onlyOwner() {
        require(msg.sender == owner, "Not authorized");
        _;
    }

    constructor() {
        owner = msg.sender;
        IERC20(USDC).approve(address(CTF), type(uint256).max);
    }

    function splitToOutcomes(bytes32 conditionId, uint256 amount) external onlyOwner {
        require(IERC20(USDC).balanceOf(address(this)) >= amount, "Insufficient USDC balance");
        uint[] memory partition = new uint[](2);
        partition[0] = 1;
        partition[1] = 2;
        CTF.splitPosition(USDC, bytes32(0), conditionId, partition, amount);
    }

    function mergeToCollateral(bytes32 conditionId, uint256 amount) external onlyOwner {
        uint[] memory partition = new uint[](2);
        partition[0] = 1;
        partition[1] = 2;
        CTF.mergePositions(USDC, bytes32(0), conditionId, partition, amount);
    }

    function withdrawUSDC(uint256 amount) external onlyOwner {
        IERC20(USDC).transfer(owner, amount);
    }
}
