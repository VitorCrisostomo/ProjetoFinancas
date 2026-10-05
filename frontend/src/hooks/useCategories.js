import useCollection from './useCollection.js';
import * as categoryService from '../services/categoryService.js';
import { readResponse } from '../services/api.js';

const loadCategories = async () => readResponse(await categoryService.fetchCategories());

export default function useCategories() {
  const { items: categories, execute, ...state } = useCollection(loadCategories);
  const save = (request) => execute(async () => readResponse(await request()), (previous, category) => (
    [...previous.filter((item) => item.id !== category.id), category]
      .sort((a, b) => a.name.localeCompare(b.name, 'pt-BR'))
  ));
  return {
    categories, ...state,
    createCategory: (name) => save(() => categoryService.createCategory(name)),
    createSubcategory: (id, name) => save(() => categoryService.createSubcategory(id, name)),
  };
}
