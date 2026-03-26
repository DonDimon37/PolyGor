// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/token/ERC1155/IERC1155.sol";
import "@openzeppelin/contracts/token/ERC1155/utils/ERC1155Holder.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title PolymarketAutomator
 * @dev Исправленная версия с учетом аудита безопасности.
 * Внедрена поддержка ERC-1155, SafeERC20 и управления владением.
 */
contract PolymarketAutomator is Ownable, ERC1155Holder {
    using SafeERC20 for IERC20;

    address public constant USDC = 0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174; // Polygon USDC
    address public immutable CTF; // Conditional Tokens Framework address

    event TokensRedeemed(address indexed operator, uint256 amount);
    event EmergencyWithdrawal(address indexed token, uint256 amount);

    constructor(address _ctf) Ownable(msg.sender) {
        require(_ctf != address(0), "Invalid CTF address");
        CTF = _ctf;
        
        // Безопасное одобрение (SafeApprove) для CTF
        IERC20(USDC).safeApprove(_ctf, type(uint256).max);
    }

    /**
     * @dev Вывод USDC с проверкой возвращаемого значения (Finding #2).
     */
    function withdrawUSDC(uint256 amount) external onlyOwner {
        IERC20(USDC).safeTransfer(owner(), amount);
    }

    /**
     * @dev Передача условных токенов ERC-1155 (Finding #1).
     * Позволяет выводить токены из контракта после сплита.
     */
    function transferConditionalTokens(
        address to,
        uint256 id,
        uint256 amount,
        bytes calldata data
    ) external onlyOwner {
        IERC1155(CTF).safeTransferFrom(address(this), to, id, amount, data);
    }

    /**
     * @dev Пакетная передача токенов ERC-1155 (Finding #1).
     */
    function safeBatchTransferConditionalTokens(
        address to,
        uint256[] calldata ids,
        uint256[] calldata amounts,
        bytes calldata data
    ) external onlyOwner {
        IERC1155(CTF).safeBatchTransferFrom(address(this), to, ids, amounts, data);
    }

    /**
     * @dev Экстренный вывод любых застрявших ERC20 токенов.
     */
    function emergencyRecoverERC20(address tokenAddress, uint256 amount) external onlyOwner {
        IERC20(tokenAddress).safeTransfer(owner(), amount);
    }

    /**
     * @dev Настройка аппрува для CTF (решение проблемы бесконечного аппрува).
     */
    function updateCTFAllowance(uint256 amount) external onlyOwner {
        IERC20(USDC).safeApprove(CTF, amount);
    }
}
